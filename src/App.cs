using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using System.Windows.Forms;

namespace Tap2Trd {
    internal partial class MainForm : Form {
        readonly Color surface = SystemColors.Window;
        readonly Color muted = SystemColors.GrayText;
        readonly DataGridView grid = new DataGridView();
        readonly PixelPreview preview = new PixelPreview();
        readonly TextBox title = new TextBox();
        readonly TextBox log = new TextBox();
        readonly Label status = new Label();
        readonly Label count = new Label();
        readonly ProgressBar progress = new ProgressBar();
        readonly CheckBox dither = new CheckBox();
        readonly List<Control> locked = new List<Control>();
        readonly Button cancel = new Button();
        readonly Button showOutput = new Button();
        readonly Button help = new Button();
        readonly JavaScriptSerializer json = new JavaScriptSerializer { MaxJsonLength = 8 * 1024 * 1024 };
        byte[] background = SpectrumScreen.DefaultBackground();
        string backgroundSource;
        string lastOutput;
        Process worker;
        bool busy, cancelled;

        internal MainForm(string[] args) {
            UiText.Language = "ru";
            ClientSize = new Size(1220, 900);
            MinimumSize = new Size(1160, 820);
            StartPosition = FormStartPosition.CenterScreen;
            AutoScaleMode = AutoScaleMode.Dpi;
            BackColor = SystemColors.Control;
            ForeColor = SystemColors.ControlText;
            Font = new Font(SystemFonts.MessageBoxFont.FontFamily, 10);
            Icon = applicationIcon;
            BuildLayout();
            InitializeLanguage();
            HelpRequested += delegate(object sender, HelpEventArgs e) { OpenHelp(); e.Handled = true; };
            AllowDrop = true;
            DragEnter += delegate(object sender, DragEventArgs e) { if (!busy && e.Data.GetDataPresent(DataFormats.FileDrop)) e.Effect = DragDropEffects.Copy; };
            DragDrop += delegate(object sender, DragEventArgs e) { if (!busy) AddFiles((string[])e.Data.GetData(DataFormats.FileDrop)); };
            FormClosing += delegate(object sender, FormClosingEventArgs e) {
                if (busy) { e.Cancel = true; CancelWork(); status.Text = UiText.T("Отмена… Закройте окно после остановки."); }
            };
            Shown += delegate { if (args.Length > 0) AddFiles(args); };
            UpdatePreview();
        }
        Label Label(string text, int size, Color color) {
            return new Label { Text = text, AutoSize = true, ForeColor = color, Font = new Font(SystemFonts.MessageBoxFont.FontFamily, size), Margin = new Padding(0, 8, 0, 8) };
        }
        Button Button(string text, EventHandler action, bool primary) {
            var b = new Button { Text = text, AutoSize = true, MinimumSize = new Size(100, 36), Height = 36,
                FlatStyle = FlatStyle.System, UseVisualStyleBackColor = true,
                ForeColor = SystemColors.ControlText, Margin = new Padding(0, 4, 8, 4) };
            if (primary) b.Font = new Font(Font, FontStyle.Bold);
            b.Click += action; locked.Add(b); return b;
        }
        void BuildLayout() {
            var root = new TableLayoutPanel { Dock = DockStyle.Fill, Padding = new Padding(24, 12, 24, 24), ColumnCount = 1, RowCount = 3 };
            root.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
            root.RowStyles.Add(new RowStyle(SizeType.Absolute, 32));
            root.RowStyles.Add(new RowStyle(SizeType.Absolute, 52));
            Controls.Add(root);
            var content = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 2, RowCount = 1 };
            content.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 52));
            content.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 48));
            root.Controls.Add(content, 0, 0);
            var left = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 1, RowCount = 5, Padding = new Padding(0, 0, 18, 0) };
            left.RowStyles.Add(new RowStyle(SizeType.Absolute, 42)); left.RowStyles.Add(new RowStyle(SizeType.Absolute, 46));
            left.RowStyles.Add(new RowStyle(SizeType.Percent, 64)); left.RowStyles.Add(new RowStyle(SizeType.Absolute, 176));
            left.RowStyles.Add(new RowStyle(SizeType.Percent, 36));
            content.Controls.Add(left, 0, 0);
            count.Text = UiText.T("01  ПРОГРАММЫ · 0"); count.Dock = DockStyle.Fill; count.ForeColor = muted; count.TextAlign = ContentAlignment.MiddleLeft;
            left.Controls.Add(count, 0, 0);
            var actions = new FlowLayoutPanel { Dock = DockStyle.Fill, WrapContents = false };
            actions.Controls.Add(Button("+ TAP / TZX", delegate { BrowseTapes(); }, false));
            actions.Controls.Add(Button(UiText.T("Убрать"), delegate { RemoveSelected(); }, false));
            var up = Button("↑", delegate { MoveSelected(-1); }, false); up.MinimumSize = new Size(36, 36); up.Width = 36; actions.Controls.Add(up);
            var down = Button("↓", delegate { MoveSelected(1); }, false); down.MinimumSize = new Size(36, 36); down.Width = 36; actions.Controls.Add(down);
            left.Controls.Add(actions, 0, 1);
            grid.Dock = DockStyle.Fill; grid.BackgroundColor = surface; grid.BorderStyle = BorderStyle.FixedSingle;
            grid.EnableHeadersVisualStyles = true; grid.ColumnHeadersDefaultCellStyle.BackColor = SystemColors.Control;
            grid.ColumnHeadersDefaultCellStyle.ForeColor = SystemColors.ControlText;
            grid.ColumnHeadersHeightSizeMode = DataGridViewColumnHeadersHeightSizeMode.AutoSize;
            grid.DefaultCellStyle.BackColor = surface; grid.DefaultCellStyle.ForeColor = SystemColors.WindowText;
            grid.DefaultCellStyle.SelectionBackColor = SystemColors.Highlight; grid.DefaultCellStyle.SelectionForeColor = SystemColors.HighlightText;
            grid.GridColor = SystemColors.ControlDark; grid.RowTemplate.Height = 38;
            grid.RowHeadersVisible = false; grid.AllowUserToAddRows = false; grid.AllowUserToDeleteRows = false;
            grid.AllowUserToResizeRows = false; grid.MultiSelect = false; grid.SelectionMode = DataGridViewSelectionMode.FullRowSelect;
            grid.AutoSizeColumnsMode = DataGridViewAutoSizeColumnsMode.Fill;
            grid.Columns.Add(new DataGridViewTextBoxColumn { Name = "Title", HeaderText = UiText.T("Название в меню"), FillWeight = 34, MaxInputLength = 29, SortMode = DataGridViewColumnSortMode.NotSortable });
            var model = new DataGridViewComboBoxColumn { Name = "Model", HeaderText = UiText.T("Модель"), Visible = false };
            model.Items.AddRange("auto", "48", "128"); grid.Columns.Add(model);
            grid.Columns.Add(new DataGridViewTextBoxColumn { Name = "Start", Visible = false });
            grid.Columns.Add(new DataGridViewTextBoxColumn { Name = "State", HeaderText = UiText.T("Состояние"), FillWeight = 25, ReadOnly = true, SortMode = DataGridViewColumnSortMode.NotSortable });
            foreach (var spec in new[] { new[] {"Tape", UiText.T("Файл")}, new[] {"Ram", "RAM"}, new[] {"Disk", UiText.T("Диск")} }) {
                var col = new DataGridViewTextBoxColumn { Name = spec[0], HeaderText = spec[1] + UiText.T("\nКиБ"), FillWeight = 13,
                    ReadOnly = true, SortMode = DataGridViewColumnSortMode.NotSortable };
                col.DefaultCellStyle.Alignment = DataGridViewContentAlignment.MiddleRight; grid.Columns.Add(col);
            }
            grid.Columns.Add(new DataGridViewTextBoxColumn { Name = "Transfer", Visible = false });
            grid.CellValueChanged += delegate(object sender, DataGridViewCellEventArgs e) { if (e.ColumnIndex == 0) UpdatePreview(); };
            grid.CurrentCellChanged += delegate { SyncGameOptions(); FollowSelectedGamePage(); };
            grid.CurrentCellDirtyStateChanged += delegate { if (grid.IsCurrentCellDirty) grid.CommitEdit(DataGridViewDataErrorContexts.Commit); };
            grid.DataError += delegate(object sender, DataGridViewDataErrorEventArgs e) { e.ThrowException = false; };
            grid.CellValidating += delegate(object sender, DataGridViewCellValidatingEventArgs e) {
                if (e.ColumnIndex == 0) {
                    string v = Convert.ToString(e.FormattedValue);
                    if (String.IsNullOrWhiteSpace(v) || v.Any(c => !SpectrumScreen.Supported(c))) {
                        e.Cancel = true; status.Text = UiText.T("Введите название: русские или латинские буквы, цифры и обычные знаки.");
                    }
                }
            };
            left.Controls.Add(grid, 0, 2); locked.Add(grid);
            left.Controls.Add(BuildGameOptions(), 0, 3);
            var right = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 1, RowCount = 2, Margin = Padding.Empty };
            right.RowStyles.Add(new RowStyle(SizeType.Absolute, 164));
            right.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
            right.Controls.Add(BuildBranding(), 0, 0);
            menuEditor = BuildMenuEditor(); right.Controls.Add(menuEditor, 0, 1);
            content.Controls.Add(right, 1, 0);
            log.Dock = DockStyle.Fill; log.Multiline = true; log.ReadOnly = true; log.ScrollBars = ScrollBars.Vertical;
            log.BackColor = surface; log.ForeColor = SystemColors.WindowText; log.BorderStyle = BorderStyle.FixedSingle; log.Font = new Font("Consolas", 9);
            log.Margin = new Padding(3, 8, 3, 0); log.AccessibleName = UiText.T("Журнал");
            log.Text = UiText.T("TAP и TZX: модель 48К/128К выбирается автоматически. Лимит загрузки — 20 минут времени Spectrum.\r\nПроизвольная подгрузка и запись на кассету не переносятся. После сборки проверьте запуск.");
            left.Controls.Add(log, 0, 4);
            status.Text = UiText.T("Добавьте программы, выберите фон и создайте TRD."); status.ForeColor = muted; status.Dock = DockStyle.Fill; status.TextAlign = ContentAlignment.MiddleLeft;
            root.Controls.Add(status, 0, 1);
            var footer = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 6, RowCount = 1 };
            footer.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
            footer.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 170)); footer.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 190));
            footer.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 110));
            footer.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100)); footer.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 190));
            footer.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 110));
            var build = Button(UiText.T("Создать TRD"), async delegate { await BuildDisk(false); }, true); build.AutoSize = false; build.Dock = DockStyle.Fill; footer.Controls.Add(build, 0, 0);
            var measure = Button(UiText.T("Рассчитать размер"), async delegate { await BuildDisk(true); }, false); measure.AutoSize = false; measure.Dock = DockStyle.Fill; footer.Controls.Add(measure, 1, 0);
            cancel.Text = UiText.T("Отмена"); cancel.FlatStyle = FlatStyle.System; cancel.UseVisualStyleBackColor = true; cancel.Enabled = false; cancel.Dock = DockStyle.Fill; cancel.Margin = new Padding(0,4,8,4);
            cancel.Click += delegate { CancelWork(); }; footer.Controls.Add(cancel, 2, 0);
            progress.Dock = DockStyle.Fill; progress.Margin = new Padding(10, 15, 20, 15); footer.Controls.Add(progress, 3, 0);
            showOutput.Text = UiText.T("Открыть папку TRD"); showOutput.Enabled = false; showOutput.FlatStyle = FlatStyle.System; showOutput.UseVisualStyleBackColor = true; showOutput.Dock = DockStyle.Fill; showOutput.Margin = new Padding(0,4,8,4);
            showOutput.Click += delegate { if (lastOutput != null) Process.Start("explorer.exe", "/select,\"" + lastOutput + "\""); }; footer.Controls.Add(showOutput, 4, 0);
            help.Text = UiText.T("Помощь"); help.FlatStyle = FlatStyle.System; help.UseVisualStyleBackColor = true;
            help.Dock = DockStyle.Fill; help.Margin = new Padding(0, 4, 0, 4);
            help.Click += delegate { OpenHelp(); }; footer.Controls.Add(help, 5, 0);
            root.Controls.Add(footer, 0, 2);
        }
        void BrowseTapes() { using (var d = new OpenFileDialog { Filter = UiText.T("Кассеты Spectrum (*.tap;*.tzx)|*.tap;*.tzx|TAP (*.tap)|*.tap|TZX (*.tzx)|*.tzx"), Multiselect = true, Title = UiText.T("Добавить программы") }) if (d.ShowDialog(this) == DialogResult.OK) AddFiles(d.FileNames); }
        void AddFiles(string[] paths) {
            foreach (string path in paths) {
                string extension = Path.GetExtension(path);
                if (!File.Exists(path) || !(extension.Equals(".tap", StringComparison.OrdinalIgnoreCase) || extension.Equals(".tzx", StringComparison.OrdinalIgnoreCase))) { AppendLog(UiText.T("Пропущен файл (нужен TAP или TZX): ") + path); continue; }
                string full = Path.GetFullPath(path);
                if (grid.Rows.Cast<DataGridViewRow>().Any(r => String.Equals((string)r.Tag, full, StringComparison.OrdinalIgnoreCase))) continue;
                int n = grid.Rows.Add(SpectrumScreen.Text(Path.GetFileNameWithoutExtension(full), 29), "auto", "", UiText.T("Не проверено"),
                    KiB(new FileInfo(full).Length), "—", "—", "auto");
                grid.Rows[n].Tag = full; grid.Rows[n].Cells[0].ToolTipText = full;
            }
            SyncGameOptions(); UpdatePreview();
        }
        void RemoveSelected() { if (grid.CurrentRow != null) grid.Rows.Remove(grid.CurrentRow); UpdatePreview(); }
        void MoveSelected(int delta) {
            if (grid.CurrentRow == null || !grid.EndEdit()) return;
            int from = grid.CurrentRow.Index, to = from + delta;
            if (to < 0 || to >= grid.Rows.Count) return;
            var row = grid.Rows[from]; grid.Rows.RemoveAt(from); grid.Rows.Insert(to, row);
            grid.CurrentCell = row.Cells[0]; UpdatePreview();
        }
        void UpdatePreview() {
            if (preview == null || background == null) return;
            RefreshPages();
            RefreshElementList();
            byte[] s = ComposeMenu();
            preview.Menu = menuLayout; preview.ItemCount = PageItemCount(previewPage); preview.PageCount = PageCount;
            preview.ShowBitmap(SpectrumScreen.Render(s));
            count.Text = UiText.T("01  ПРОГРАММЫ · ") + grid.Rows.Count + UiText.T(" · СТРАНИЦ: ") + PageCount;
            if (directLaunch) count.Text = UiText.T("01  ПРОГРАММЫ · ") + grid.Rows.Count + UiText.T(" · БЕЗ МЕНЮ");
            string error = ValidateMenu();
            layoutWarning.Text = error ?? (PageCount > 1 ? UiText.T("На Spectrum: P — назад, N — далее, по кругу. Надписи можно перетаскивать.")
                : UiText.T("Перетащите надпись мышью. Переходы появятся при двух страницах."));
            layoutWarning.ForeColor = error == null ? muted : Color.Firebrick;
        }
        void LoadBackground() {
            using (var d = new OpenFileDialog { Filter = UiText.T("Изображения и Spectrum SCR|*.png;*.jpg;*.jpeg;*.bmp;*.scr"), Title = UiText.T("Фон меню · центр изображения будет обрезан до 4:3") }) {
                if (d.ShowDialog(this) != DialogResult.OK) return;
                backgroundSource = d.FileName; ConvertBackground();
            }
        }
        void ConvertBackground() {
            try { background = SpectrumScreen.ConvertImage(backgroundSource, dither.Checked); UpdatePreview(); status.Text = UiText.T("Фон подготовлен: 256 × 192, 6912 байт."); }
            catch (Exception ex) { MessageBox.Show(this, ex.Message, UiText.T("Не удалось открыть фон"), MessageBoxButtons.OK, MessageBoxIcon.Warning); backgroundSource = null; }
        }
        void ExportBackground() {
            using (var d = new SaveFileDialog { Filter = "Spectrum screen (*.scr)|*.scr", FileName = "menu.scr", OverwritePrompt = true }) {
                if (d.ShowDialog(this) != DialogResult.OK) return;
                try { File.WriteAllBytes(d.FileName, background); status.Text = UiText.T("Фон сохранён: ") + d.FileName; }
                catch (Exception ex) { MessageBox.Show(this, ex.Message, UiText.T("Ошибка записи"), MessageBoxButtons.OK, MessageBoxIcon.Error); }
            }
        }
        void AppendLog(string text) { log.AppendText("\r\n" + text); log.SelectionStart = log.TextLength; log.ScrollToCaret(); }
        string HelpPath { get { return Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "help", UiText.Language == "en" ? "index.en.html" : "index.ru.html"); } }
        void OpenHelp() {
            try {
                if (!File.Exists(HelpPath)) throw new FileNotFoundException();
                Process.Start(new ProcessStartInfo(HelpPath) { UseShellExecute = true });
            } catch (Exception ex) {
                if (!(ex is IOException) && !(ex is System.ComponentModel.Win32Exception) && !(ex is UnauthorizedAccessException)) throw;
                status.Text = UiText.T("Не удалось открыть справку. Откройте HTML-файл в папке help рядом с программой.");
                AppendLog(status.Text + "\r\n" + HelpPath);
            }
        }
        void SetBusy(bool value) { busy = value; foreach (var c in locked) c.Enabled = !value; menuEditor.Enabled = !value && !directLaunch; cancel.Enabled = value; UseWaitCursor = value; SyncGameOptions(); }
        async Task BuildDisk(bool measure) {
            if (busy || !grid.EndEdit()) return;
            if (grid.Rows.Count == 0) { status.Text = UiText.T("Сначала добавьте TAP или TZX."); return; }
            if (directLaunch && grid.Rows.Count != 1) { status.Text = UiText.T("Для запуска без меню оставьте одну программу в списке."); return; }
            if (grid.Rows.Cast<DataGridViewRow>().Any(r => String.IsNullOrWhiteSpace(Convert.ToString(r.Cells[0].Value)))) { status.Text = UiText.T("Введите названия всех программ."); return; }
            string layoutError = directLaunch ? null : ValidateMenu();
            if (layoutError != null) { status.Text = layoutError; return; }
            string target = null;
            var games = new List<object>();
            foreach (DataGridViewRow r in grid.Rows) {
                string start = Convert.ToString(r.Cells[2].Value).Trim();
                int address;
                if (start.Length > 0 && (!TryAddress(start, out address) || address < 0 || address > 65535)) { status.Text = UiText.T("Некорректный адрес старта: ") + start; return; }
                games.Add(new { path = (string)r.Tag, title = Convert.ToString(r.Cells[0].Value), machine = Convert.ToString(r.Cells[1].Value),
                    start = start, transfer_mode = Convert.ToString(r.Cells["Transfer"].Value) });
            }
            if (!measure) using (var d = new SaveFileDialog { Filter = "TR-DOS disk (*.trd)|*.trd", FileName = "Collection.trd", OverwritePrompt = true }) {
                if (d.ShowDialog(this) != DialogResult.OK) return; target = d.FileName;
            }
            foreach (DataGridViewRow r in grid.Rows) { InvalidateSize(r); r.Cells["State"].Value = UiText.T("В очереди"); }
            var request = new { action = measure ? "measure" : "build", language = UiText.Language, output = target, overwrite = true, title = SpectrumScreen.Text(title.Text, 32), games = games, background = Convert.ToBase64String(background),
                launch_mode = directLaunch ? "direct" : "menu",
                pages = menuPages.Take(PageCount).Select((page, i) => page.Copy(PageItemCount(i))).ToList() };
            string serialized = json.Serialize(request);
            var ascii = new StringBuilder();
            foreach (char c in serialized) { if (c > 127) ascii.Append("\\u" + ((int)c).ToString("x4")); else ascii.Append(c); }
            SetBusy(true); cancelled = false; progress.Value = 0; log.Clear();
            status.Text = UiText.T("Подготовка конвертера…");
            try { await Task.Run(() => RunWorker(ascii.ToString())); }
            catch (Exception ex) { AppendLog(ex.Message); status.Text = cancelled ? UiText.T("Операция отменена.") : UiText.T("Операция не завершена. Подробности в журнале."); }
            finally {
                foreach (DataGridViewRow r in grid.Rows)
                    if (Convert.ToString(r.Cells["State"].Value) == UiText.T("Загрузка…") || Convert.ToString(r.Cells["State"].Value) == UiText.T("В очереди"))
                        r.Cells["State"].Value = cancelled ? UiText.T("Отменено") : UiText.T("Не завершено");
                worker = null; SetBusy(false);
            }
        }
        static bool TryAddress(string value, out int n) {
            return value.StartsWith("0x", StringComparison.OrdinalIgnoreCase) ? Int32.TryParse(value.Substring(2), System.Globalization.NumberStyles.HexNumber, null, out n) : Int32.TryParse(value, out n);
        }
        void RunWorker(string input) {
            string exe = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "engine", "TaRDulator.Engine.exe");
            if (!File.Exists(exe)) throw new FileNotFoundException(UiText.T("Не найден engine\\TaRDulator.Engine.exe. Распакуйте всю папку приложения."));
            var psi = new ProcessStartInfo(exe) { UseShellExecute = false, CreateNoWindow = true, RedirectStandardInput = true, RedirectStandardOutput = true, RedirectStandardError = true, WorkingDirectory = Path.GetDirectoryName(exe) };
            using (var p = Process.Start(psi)) {
                worker = p;
                if (cancelled) { KillWorker(p); throw new OperationCanceledException(); }
                p.StandardInput.Write(input); p.StandardInput.Close();
                Task<string> errors = p.StandardError.ReadToEndAsync();
                string line; bool completed = false;
                while ((line = p.StandardOutput.ReadLine()) != null) {
                    var item = json.Deserialize<Dictionary<string, object>>(line);
                    string kind = Convert.ToString(item["event"]);
                    if (kind == "result") completed = true;
                    Invoke(new Action(() => OnEvent(item)));
                }
                p.WaitForExit();
                string stderr = errors.Result;
                if (stderr.Length > 0) Invoke(new Action(() => AppendLog(stderr)));
                if (cancelled) throw new OperationCanceledException(UiText.T("Операция отменена пользователем."));
                if (p.ExitCode != 0 || !completed) throw new InvalidOperationException(UiText.T("Конвертер не завершил операцию. Исходные кассеты сохранены."));
            }
        }
        void OnEvent(Dictionary<string, object> e) {
            string kind = Convert.ToString(e["event"]);
            if (kind == "progress") {
                int i = Convert.ToInt32(e["index"]); grid.Rows[i].Cells[3].Value = UiText.T("Загрузка…");
                status.Text = Convert.ToString(e["text"]); AppendLog(status.Text); progress.Value = i * 100 / grid.Rows.Count;
            } else if (kind == "profile") {
                AppendLog("  SHA-256: " + e["sha256"]);
                if (Convert.ToString(e["profile_title"]).Length > 0)
                    AppendLog("  " + e["profile_title"] + ": " + e["profile_description"]);
            } else if (kind == "loading") {
                status.Text = Convert.ToString(e["text"]); AppendLog("  " + status.Text);
            } else if (kind == "game") {
                int i = Convert.ToInt32(e["index"]); bool warning = Convert.ToString(e["warning"]).Length > 0;
                var row = grid.Rows[i];
                row.Cells["State"].Value = warning ? UiText.T("Проверить") : UiText.T("Готово");
                row.Cells["State"].ToolTipText = Convert.ToString(e["warning"]);
                row.Cells["Tape"].Value = KiB(Convert.ToInt64(e["tap_bytes"]));
                row.Cells["Ram"].Value = KiB(Convert.ToInt64(e["ram_bytes"]));
                row.Cells["Disk"].Value = KiB(Convert.ToInt64(e["bytes"]));
                row.Cells["Disk"].Tag = e;
                row.Cells["Disk"].ToolTipText = UiText.T("С загрузчиком и округлением до секторов по 256 байт.");
                SyncGameOptions();
                AppendLog("  " + e["title"] + ": RAM " + row.Cells["Ram"].Value + UiText.T(" → диск ") + row.Cells["Disk"].Value
                    + UiText.T(" КиБ; перенос ") + (Convert.ToString(e["result_machine"]) == "" ? UiText.T("не определён") : e["result_machine"] + UiText.T("К")) + "; PC=" + e["pc"]);
                AppendLog("  " + e["model_reason"]);
                if (e.ContainsKey("strategy_name")) AppendLog("  " + e["strategy_name"]);
                if (e.ContainsKey("profile_note")) AppendLog("  " + e["profile_note"]);
                if (warning) AppendLog("  " + e["warning"]);
            } else if (kind == "game_error") {
                int i = Convert.ToInt32(e["index"]);
                var row = grid.Rows[i];
                row.Cells["State"].Value = UiText.T(Convert.ToBoolean(e["unsupported"]) ? "Не поддерживается" : "Ошибка загрузки");
                row.Cells["State"].ToolTipText = Convert.ToString(e["message"]);
            } else if (kind == "error") {
                AppendLog(UiText.T("ОШИБКА: ") + e["message"]);
            } else if (kind == "result") {
                progress.Value = 100;
                bool measured = Convert.ToString(e["action"]) == "measure";
                status.Text = (measured ? UiText.T("Расчёт готов") : UiText.T("Диск создан")) + " · " + KiB(Convert.ToInt64(e["used_bytes"]))
                    + UiText.T(" / 636 КиБ · файлов ") + e["file_count"] + UiText.T(" / 128 · страниц ") + e["page_count"];
                if (measured) { AppendLog(status.Text + UiText.T(". TRD не записан; при сборке расчёт повторится.")); return; }
                lastOutput = Convert.ToString(e["output"]); showOutput.Enabled = true;
                AppendLog(lastOutput); AppendLog(UiText.T(e.ContainsKey("launch_mode") && Convert.ToString(e["launch_mode"]) == "direct"
                    ? "Запуск в TR-DOS: RUN. Программа стартует сразу, без выбора в меню."
                    : "Запуск в TR-DOS: RUN \"boot\". Выбор: 1–9, A–G; страницы: P — назад, N — далее."));
                if (e.ContainsKey("report_warning")) AppendLog(UiText.T("Диск создан, но отчёт не записан: ") + e["report_warning"]);
                else AppendLog(UiText.T("Отчёт о загрузке сохранён рядом с TRD. Снимок ещё не означает проверку всей игры."));
            }
        }
        void CancelWork() {
            cancelled = true; cancel.Enabled = false; status.Text = UiText.T("Остановка…");
            Process p = worker; if (p != null) KillWorker(p);
        }
        static void KillWorker(Process p) {
            try {
                if (!p.HasExited) using (var killer = Process.Start(new ProcessStartInfo("taskkill.exe", "/PID " + p.Id + " /T /F") { UseShellExecute = false, CreateNoWindow = true })) { killer.WaitForExit(5000); }
            } catch (InvalidOperationException) { } catch (System.ComponentModel.Win32Exception) { }
        }
    }
    internal static class Program {
        [STAThread] static void Main(string[] args) {
            Application.EnableVisualStyles(); Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new MainForm(args));
        }
    }
}
