using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Windows.Forms;

namespace Tap2Trd {
    internal partial class MainForm {
        List<MenuLayout> menuPages = new List<MenuLayout> { MenuLayout.Default(16) };
        int previewPage;
        MenuLayout menuLayout { get { return menuPages[previewPage]; } set { menuPages[previewPage] = value; } }
        readonly ComboBox pageChoice = new ComboBox();
        bool syncingPage;
        int PageCount { get { return Math.Max(1, (grid.Rows.Count + 15) / 16); } }
        int PageItemCount(int page) { return Math.Max(0, Math.Min(16, grid.Rows.Count - page * 16)); }
        readonly ComboBox elementChoice = new ComboBox();
        readonly TextBox elementText = new TextBox();
        readonly NumericUpDown elementX = new NumericUpDown(), elementY = new NumericUpDown(), elementWidth = new NumericUpDown();
        readonly CheckBox elementVisible = new CheckBox(), elementBright = new CheckBox();
        readonly ComboBox elementInk = new ComboBox(), elementPaper = new ComboBox();
        readonly Label layoutWarning = new Label();
        bool syncingEditor;

        FlowLayoutPanel EditorRow() { return new FlowLayoutPanel { Dock = DockStyle.Fill, WrapContents = false, Margin = Padding.Empty }; }
        ComboBox ColorChoice(ComboBox choice) {
            choice.DropDownStyle = ComboBoxStyle.DropDownList; choice.Width = 112;
            choice.Items.AddRange(new object[] { UiText.T("Чёрный"), UiText.T("Синий"), UiText.T("Красный"), UiText.T("Пурпурный"), UiText.T("Зелёный"), UiText.T("Голубой"), UiText.T("Жёлтый"), UiText.T("Белый") });
            choice.SelectedIndex = 0; choice.SelectedIndexChanged += delegate { ApplyEditor(); }; return choice;
        }
        Control BuildMenuEditor() {
            var right = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 1, RowCount = 4, Padding = new Padding(8, 0, 0, 0) };
            right.RowStyles.Add(new RowStyle(SizeType.Absolute, 66));
            right.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
            right.RowStyles.Add(new RowStyle(SizeType.Absolute, 48));
            right.RowStyles.Add(new RowStyle(SizeType.Absolute, 212));
            var heading = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 1, RowCount = 2, Margin = Padding.Empty };
            heading.RowStyles.Add(new RowStyle(SizeType.Absolute, 32)); heading.RowStyles.Add(new RowStyle(SizeType.Absolute, 32));
            heading.Controls.Add(Label(UiText.T("02  РЕДАКТОР МЕНЮ · РУССКИЙ / ENGLISH"), 10, muted), 0, 0);
            pageChoice.DropDownStyle = ComboBoxStyle.DropDownList; pageChoice.Dock = DockStyle.Fill;
            pageChoice.AccessibleName = UiText.T("Страница меню"); locked.Add(pageChoice);
            pageChoice.SelectedIndexChanged += delegate {
                if (syncingPage || pageChoice.SelectedIndex < 0) return;
                previewPage = pageChoice.SelectedIndex; elementChoice.SelectedIndex = -1; UpdatePreview();
            };
            heading.Controls.Add(pageChoice, 0, 1); right.Controls.Add(heading, 0, 0);
            title.Text = "КОЛЛЕКЦИЯ ИГР";
            preview.Dock = DockStyle.Fill; preview.Margin = new Padding(0, 4, 0, 4); right.Controls.Add(preview, 0, 1); locked.Add(preview);
            preview.SelectElement = delegate(int index) { elementChoice.SelectedIndex = index; };
            preview.MoveElement = delegate(int index, int x, int y) {
                menuLayout.At(index).x = x; menuLayout.At(index).y = y; SyncEditor(); UpdatePreview();
            };
            layoutWarning.Dock = DockStyle.Fill; layoutWarning.Font = new Font(SystemFonts.MessageBoxFont.FontFamily, 9); layoutWarning.TextAlign = ContentAlignment.MiddleLeft;
            right.Controls.Add(layoutWarning, 0, 2);
            var tabs = new TabControl { Dock = DockStyle.Fill }; locked.Add(tabs); right.Controls.Add(tabs, 0, 3);
            var position = new TabPage(UiText.T("Размещение")) { BackColor = BackColor, ForeColor = ForeColor, Padding = new Padding(4) };
            var layout = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 1, RowCount = 5 };
            foreach (int height in new[] { 30, 30, 32, 32, 42 }) layout.RowStyles.Add(new RowStyle(SizeType.Absolute, height));
            position.Controls.Add(layout); tabs.TabPages.Add(position);
            var selectRow = EditorRow(); elementChoice.DropDownStyle = ComboBoxStyle.DropDownList; elementChoice.Width = 265;
            elementChoice.SelectedIndexChanged += delegate { if (!syncingEditor) SyncEditor(); };
            selectRow.Controls.Add(elementChoice);
            elementVisible.Text = UiText.T("Показывать"); elementVisible.AutoSize = true; elementVisible.CheckedChanged += delegate { ApplyEditor(); };
            selectRow.Controls.Add(elementVisible); layout.Controls.Add(selectRow, 0, 0);
            elementText.Dock = DockStyle.Fill; elementText.MaxLength = 32; elementText.BackColor = SystemColors.Window; elementText.ForeColor = SystemColors.WindowText;
            elementText.TextChanged += delegate {
                if (syncingEditor || elementChoice.SelectedIndex < 0) return;
                string value = SpectrumScreen.Text(elementText.Text, elementChoice.SelectedIndex >= MenuLayout.ItemOffset ? 29 : 32);
                if (elementChoice.SelectedIndex == 0) title.Text = value;
                else if (elementChoice.SelectedIndex < MenuLayout.ItemOffset) menuLayout.At(elementChoice.SelectedIndex).text = value;
                else grid.Rows[previewPage*16+elementChoice.SelectedIndex-MenuLayout.ItemOffset].Cells[0].Value = value;
                UpdatePreview();
            };
            layout.Controls.Add(elementText, 0, 1);
            var coords = EditorRow();
            coords.Controls.Add(Label("X", 9, muted)); SetupNumber(elementX, 31); coords.Controls.Add(elementX);
            coords.Controls.Add(Label("Y", 9, muted)); SetupNumber(elementY, 23); coords.Controls.Add(elementY);
            coords.Controls.Add(Label(UiText.T("Ширина"), 9, muted)); SetupNumber(elementWidth, 32); elementWidth.Minimum = 1; coords.Controls.Add(elementWidth);
            coords.Controls.Add(Label(UiText.T("яч."), 9, muted)); layout.Controls.Add(coords, 0, 2);
            var colors = EditorRow(); colors.Controls.Add(Label(UiText.T("Текст"), 9, muted)); colors.Controls.Add(ColorChoice(elementInk));
            colors.Controls.Add(Label(UiText.T("Фон"), 9, muted)); colors.Controls.Add(ColorChoice(elementPaper));
            elementBright.Text = UiText.T("Яркий"); elementBright.AutoSize = true; elementBright.CheckedChanged += delegate { ApplyEditor(); }; colors.Controls.Add(elementBright);
            layout.Controls.Add(colors, 0, 3);
            var arrange = EditorRow();
            arrange.Controls.Add(Button(UiText.T("1 колонка"), delegate { ArrangeItems(false); }, false));
            arrange.Controls.Add(Button(UiText.T("2 колонки"), delegate { ArrangeItems(true); }, false));
            var showGrid = new CheckBox { Text = UiText.T("Сетка"), AutoSize = true, Margin = new Padding(10, 12, 0, 0) };
            showGrid.CheckedChanged += delegate { preview.ShowGrid = showGrid.Checked; preview.Invalidate(); }; arrange.Controls.Add(showGrid);
            layout.Controls.Add(arrange, 0, 4);

            var imageTab = new TabPage(UiText.T("Фон и SCR")) { BackColor = BackColor, ForeColor = ForeColor, Padding = new Padding(8) };
            var imagePanel = new FlowLayoutPanel { Dock = DockStyle.Fill, FlowDirection = FlowDirection.TopDown, WrapContents = false };
            imageTab.Controls.Add(imagePanel); tabs.TabPages.Add(imageTab);
            var imageActions = new FlowLayoutPanel { AutoSize = true, WrapContents = false };
            imageActions.Controls.Add(Button(UiText.T("Загрузить фон"), delegate { LoadBackground(); }, false));
            imageActions.Controls.Add(Button(UiText.T("Сбросить фон"), delegate { backgroundSource = null; background = SpectrumScreen.DefaultBackground(); UpdatePreview(); }, false));
            imagePanel.Controls.Add(imageActions);
            dither.Text = UiText.T("Дизеринг для PNG / JPEG"); dither.AutoSize = true;
            dither.CheckedChanged += delegate { if (backgroundSource != null) ConvertBackground(); }; imagePanel.Controls.Add(dither);
            var exportActions = new FlowLayoutPanel { AutoSize = true, WrapContents = false };
            exportActions.Controls.Add(Button(UiText.T("Фон → SCR"), delegate { ExportBackground(); }, false));
            exportActions.Controls.Add(Button(UiText.T("Меню → SCR"), delegate { ExportMenu(); }, false)); imagePanel.Controls.Add(exportActions);
            imagePanel.Controls.Add(Label(UiText.T("SCR: 256 × 192. Экспортируется выбранная страница."), 9, muted));

            var templateTab = new TabPage(UiText.T("Макеты")) { BackColor = BackColor, ForeColor = ForeColor, Padding = new Padding(8) };
            var templatePanel = new FlowLayoutPanel { Dock = DockStyle.Fill, FlowDirection = FlowDirection.TopDown, WrapContents = false };
            templateTab.Controls.Add(templatePanel); tabs.TabPages.Add(templateTab);
            var templateActions = new FlowLayoutPanel { AutoSize = true, WrapContents = false };
            templateActions.Controls.Add(Button(UiText.T("Сохранить макет"), delegate { SaveTemplate(); }, false));
            templateActions.Controls.Add(Button(UiText.T("Открыть макет"), delegate { LoadTemplate(); }, false)); templatePanel.Controls.Add(templateActions);
            templatePanel.Controls.Add(Button(UiText.T("Сбросить макет страницы"), delegate { menuLayout = MenuLayout.Default(16); SyncEditor(); UpdatePreview(); }, false));
            templatePanel.Controls.Add(new Label { Text = UiText.T("Сохраняются макеты всех страниц, общий фон и заголовок.\nTAP и названия игр в макет не входят. Переходы: P / N.\nВ надписях переходов доступны {page} и {pages}."), AutoSize = true, ForeColor = muted, Font = new Font(SystemFonts.MessageBoxFont.FontFamily, 9) });
            RefreshElementList(); return right;
        }
        void SetupNumber(NumericUpDown control, int maximum) {
            control.Maximum = maximum; control.Width = 60; control.BackColor = SystemColors.Window; control.ForeColor = SystemColors.WindowText;
            control.ValueChanged += delegate { ApplyEditor(); };
        }
        void RefreshElementList() {
            int count = PageItemCount(previewPage);
            if (elementChoice.Items.Count != count + MenuLayout.ItemOffset || elementChoice.SelectedIndex < 0) {
                int selected = Math.Max(0, Math.Min(elementChoice.SelectedIndex, count + MenuLayout.ItemOffset - 1));
                syncingEditor = true; elementChoice.Items.Clear();
                elementChoice.Items.Add(UiText.T("Заголовок")); elementChoice.Items.Add(UiText.T("Подсказка о клавише"));
                elementChoice.Items.Add(UiText.T("Назад (P)")); elementChoice.Items.Add(UiText.T("Далее (N)")); elementChoice.Items.Add(UiText.T("Номер страницы"));
                for (int i = 0; i < count; i++) elementChoice.Items.Add(UiText.T("Пункт ") + MenuLayout.Keys[i] + UiText.T(" · игра ") + (previewPage*16+i+1));
                elementChoice.SelectedIndex = selected; syncingEditor = false; SyncEditor();
            } else if (!elementText.Focused) SyncEditor();
        }
        void SyncEditor() {
            if (elementChoice.SelectedIndex < 0) return;
            syncingEditor = true;
            int index = elementChoice.SelectedIndex; var s = menuLayout.At(index);
            elementText.MaxLength = index >= MenuLayout.ItemOffset ? 29 : 32;
            elementText.Text = index == 0 ? title.Text : index < MenuLayout.ItemOffset ? s.text : Convert.ToString(grid.Rows[previewPage*16+index-MenuLayout.ItemOffset].Cells[0].Value);
            elementX.Maximum = 32-s.width; elementX.Value = s.x; elementY.Value = s.y;
            elementWidth.Minimum = index >= MenuLayout.ItemOffset ? 4 : 1; elementWidth.Maximum = 32-s.x; elementWidth.Value = s.width;
            elementVisible.Enabled = index < MenuLayout.ItemOffset; elementVisible.Checked = s.visible; elementBright.Checked = s.bright;
            elementInk.SelectedIndex = s.ink; elementPaper.SelectedIndex = s.paper;
            preview.Selected = index; preview.Invalidate(); syncingEditor = false;
        }
        void ApplyEditor() {
            if (syncingEditor || elementChoice.SelectedIndex < 0) return;
            var s = menuLayout.At(elementChoice.SelectedIndex);
            s.x = (int)elementX.Value; s.y = (int)elementY.Value; s.width = (int)elementWidth.Value;
            s.visible = elementVisible.Checked; s.bright = elementBright.Checked;
            s.ink = elementInk.SelectedIndex; s.paper = elementPaper.SelectedIndex;
            SyncEditor(); UpdatePreview();
        }
        void ArrangeItems(bool twoColumns) {
            menuLayout.Arrange(PageItemCount(previewPage), twoColumns);
            SyncEditor(); UpdatePreview();
        }
        byte[] ComposeMenu() {
            return SpectrumScreen.Compose(background, title.Text, grid.Rows.Cast<DataGridViewRow>().Skip(previewPage*16).Take(16)
                .Select(r => Convert.ToString(r.Cells[0].Value)).ToArray(), menuLayout, previewPage, PageCount);
        }
        void ExportMenu() {
            string error = menuLayout.Validate(PageItemCount(previewPage), true, PageCount); if (error != null) { status.Text = error; return; }
            using (var d = new SaveFileDialog { Filter = "Spectrum screen (*.scr)|*.scr", FileName = "menu-" + (previewPage+1) + ".scr", OverwritePrompt = true }) {
                if (d.ShowDialog(this) != DialogResult.OK) return;
                try { File.WriteAllBytes(d.FileName, ComposeMenu()); status.Text = UiText.T("Экран меню сохранён: ") + d.FileName; }
                catch (Exception ex) { MessageBox.Show(this, ex.Message, UiText.T("Ошибка записи")); }
            }
        }
        void SaveTemplate() {
            if (!grid.EndEdit()) return;
            string error = ValidateMenu(); if (error != null) { status.Text = error; return; }
            using (var d = new SaveFileDialog { Filter = UiText.T("Макет ТаРДулятора (*.t2menu)|*.t2menu"), FileName = "Menu.t2menu", OverwritePrompt = true }) {
                if (d.ShowDialog(this) != DialogResult.OK) return;
                try {
                    var template = new MenuTemplate { version = 2, title = title.Text, pages = menuPages, background = Convert.ToBase64String(background) };
                    File.WriteAllText(d.FileName, json.Serialize(template), System.Text.Encoding.UTF8); status.Text = UiText.T("Макет сохранён.");
                } catch (Exception ex) { MessageBox.Show(this, ex.Message, UiText.T("Ошибка записи")); }
            }
        }
        void LoadTemplate() {
            using (var d = new OpenFileDialog { Filter = UiText.T("Макет ТаРДулятора (*.t2menu)|*.t2menu") }) {
                if (d.ShowDialog(this) != DialogResult.OK) return;
                try {
                    if (new FileInfo(d.FileName).Length > 1024*1024) throw new InvalidDataException(UiText.T("Слишком большой файл макета."));
                    var template = json.Deserialize<MenuTemplate>(File.ReadAllText(d.FileName));
                    if (template == null) throw new InvalidDataException(UiText.T("Неизвестный формат макета."));
                    var loadedPages = template.ReadPages();
                    // Old single-page templates seed new pages without changing
                    // their existing positions. Any overlap is shown for editing.
                    while (loadedPages.Count < PageCount) loadedPages.Add(loadedPages[0].Copy(16));
                    byte[] image = Convert.FromBase64String(template.background);
                    if (image.Length != 6912) throw new InvalidDataException(UiText.T("Неверный размер фона."));
                    menuPages = loadedPages; previewPage = 0;
                    foreach (var page in menuPages)
                        foreach (var item in new[] { page.hint, page.previous, page.next, page.page }) item.text = SpectrumScreen.Text(item.text ?? "", 32);
                    title.Text = SpectrumScreen.Text(template.title, 32); background = image; backgroundSource = null;
                    elementChoice.SelectedIndex = -1; UpdatePreview(); status.Text = UiText.T("Макет загружен. Позиции привязаны к странице и номеру пункта.");
                } catch (Exception ex) { MessageBox.Show(this, ex.Message, UiText.T("Не удалось открыть макет"), MessageBoxButtons.OK, MessageBoxIcon.Warning); }
            }
        }
        void RefreshPages() {
            while (menuPages.Count < PageCount) menuPages.Add(menuPages[0].Copy(16));
            previewPage = Math.Max(0, Math.Min(previewPage, PageCount-1));
            syncingPage = true;
            pageChoice.Items.Clear();
            for (int i = 0; i < PageCount; i++) pageChoice.Items.Add(UiText.T("Страница ") + (i+1) + " / " + PageCount
                + (grid.Rows.Count == 0 ? "" : UiText.T(" · игры ") + (i*16+1) + "–" + (i*16+PageItemCount(i))));
            pageChoice.SelectedIndex = previewPage; syncingPage = false;
        }
        void FollowSelectedGamePage() {
            if (busy || grid.CurrentRow == null || pageChoice.Items.Count == 0) return;
            int page = grid.CurrentRow.Index / 16;
            if (page == previewPage) return;
            previewPage = page; elementChoice.SelectedIndex = -1; UpdatePreview();
        }
        string ValidateMenu() {
            for (int i = 0; i < PageCount; i++) {
                string error = menuPages[i].Validate(PageItemCount(i), true, PageCount);
                if (error != null) return UiText.T("Страница ") + (i+1) + ": " + error;
            }
            return null;
        }
    }
}
