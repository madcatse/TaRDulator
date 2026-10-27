using System;
using System.Collections.Generic;
using System.Drawing;
using System.Windows.Forms;

namespace Tap2Trd {
    internal partial class MainForm {
        readonly ComboBox loadModel = new ComboBox(), transferMode = new ComboBox();
        readonly TextBox startAddress = new TextBox();
        readonly Label gameDetails = new Label();
        bool syncingGame;
        static readonly string[] TransferModes = { "auto", "preserve", "48" };
        static readonly string[] LoadModels = { "auto", "48", "128" };

        static string KiB(long bytes) { return (bytes / 1024.0).ToString("0.##"); }

        Control BuildGameOptions() {
            var panel = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 3, RowCount = 4, Margin = Padding.Empty };
            panel.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 112));
            panel.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
            panel.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 94));
            foreach (int height in new[] { 28, 24, 32, 86 }) panel.RowStyles.Add(new RowStyle(SizeType.Absolute, height));
            var heading = Label(UiText.T("Параметры выбранной программы"), 9, muted);
            heading.Margin = new Padding(0, 8, 0, 0); panel.Controls.Add(heading, 0, 0); panel.SetColumnSpan(heading, 3);
            string[] labels = { UiText.T("Модель"), UiText.T("Перенос на диск"), UiText.T("Старт*") };
            for (int i = 0; i < 3; i++) {
                var label = Label(labels[i], 9, muted); label.Margin = new Padding(0, 4, 0, 0); panel.Controls.Add(label, i, 1);
            }
            loadModel.DropDownStyle = transferMode.DropDownStyle = ComboBoxStyle.DropDownList;
            loadModel.AccessibleName = UiText.T("Модель для загрузки кассеты");
            transferMode.AccessibleName = UiText.T("Режим переноса на диск");
            startAddress.AccessibleName = UiText.T("Адрес старта");
            loadModel.Items.AddRange(new object[] { UiText.T("Авто"), UiText.T("48К"), UiText.T("128К") });
            transferMode.Items.AddRange(new object[] { UiText.T("Авто (Z80to)"), UiText.T("Сохранить 128К"), UiText.T("Принудительно 48К") });
            startAddress.MaxLength = 6;
            Control[] fields = { loadModel, transferMode, startAddress };
            for (int i = 0; i < 3; i++) { fields[i].Dock = DockStyle.Fill; fields[i].Margin = new Padding(0, 2, i == 2 ? 0 : 8, 2); panel.Controls.Add(fields[i], i, 2); locked.Add(fields[i]); }
            loadModel.SelectedIndexChanged += delegate { ApplyGameOptions(); };
            transferMode.SelectedIndexChanged += delegate { ApplyGameOptions(); };
            startAddress.TextChanged += delegate { ApplyGameOptions(); };
            gameDetails.Dock = DockStyle.Fill; gameDetails.Font = new Font(Font.FontFamily, 9); gameDetails.ForeColor = muted;
            gameDetails.Margin = new Padding(0, 6, 0, 0); panel.Controls.Add(gameDetails, 0, 3); panel.SetColumnSpan(gameDetails, 3);
            SyncGameOptions();
            return panel;
        }
        void SyncGameOptions() {
            if (transferMode.Items.Count == 0) return;
            syncingGame = true;
            var row = grid.CurrentRow;
            loadModel.Enabled = transferMode.Enabled = startAddress.Enabled = row != null && !busy;
            loadModel.SelectedIndex = row == null ? -1 : Math.Max(0, Array.IndexOf(LoadModels, Convert.ToString(row.Cells["Model"].Value)));
            transferMode.SelectedIndex = row == null ? -1 : Math.Max(0, Array.IndexOf(TransferModes, Convert.ToString(row.Cells["Transfer"].Value)));
            startAddress.Text = row == null ? "" : Convert.ToString(row.Cells["Start"].Value);
            syncingGame = false;
            UpdateGameDetails();
        }
        void InvalidateSize(DataGridViewRow row) {
            row.Cells["Ram"].Value = row.Cells["Disk"].Value = "—";
            row.Cells["Disk"].Tag = null; row.Cells["Disk"].ToolTipText = "";
            row.Cells["State"].Value = UiText.T("Не проверено"); row.Cells["State"].ToolTipText = "";
        }
        void ApplyGameOptions() {
            if (syncingGame || busy || grid.CurrentRow == null || loadModel.SelectedIndex < 0 || transferMode.SelectedIndex < 0) return;
            var row = grid.CurrentRow;
            row.Cells["Model"].Value = LoadModels[loadModel.SelectedIndex];
            row.Cells["Transfer"].Value = TransferModes[transferMode.SelectedIndex];
            row.Cells["Start"].Value = startAddress.Text;
            InvalidateSize(row); UpdateGameDetails();
            status.Text = UiText.T("Параметры изменены. Рассчитайте размер заново или создайте TRD.");
        }
        void UpdateGameDetails() {
            var row = grid.CurrentRow;
            string description = UiText.T("Авто проверяет загрузку и дополнительные банки памяти.\nЛимит: 20 минут времени Spectrum (с ускорением).\n* Старт обычно оставляют пустым. Размеры в КиБ.");
            gameDetails.ForeColor = muted;
            if (row != null) {
                var data = row.Cells["Disk"].Tag as Dictionary<string, object>;
                if (data != null) {
                    double ram = Convert.ToDouble(data["ram_bytes"]), disk = Convert.ToDouble(data["bytes"]);
                    string model = Convert.ToString(data["result_machine"]);
                    description = "RAM " + KiB((long)ram) + UiText.T(" → диск ") + KiB((long)disk) + UiText.T(" КиБ (")
                        + (100 * (1 - disk / ram)).ToString("0.0") + UiText.T("% меньше исходной RAM).\n")
                        + UiText.T("Загрузка: ") + data["load_machine"] + UiText.T("К; на диске: ") + (model == "" ? UiText.T("не определено") : model + UiText.T("К")) + ".\n"
                        + UiText.T("Причина выбора модели — в журнале. * Старт обычно пустой.");
                }
                if (Convert.ToString(row.Cells["Model"].Value) != "48" && Convert.ToString(row.Cells["Transfer"].Value) == "48") {
                    description = UiText.T("Принудительно 48К: дополнительные банки будут отброшены,\nпереключение памяти отключено. Для настоящей 128К-игры\nвыберите «Сохранить 128К». * Старт обычно пустой.");
                    gameDetails.ForeColor = Color.Firebrick;
                }
            }
            gameDetails.Text = description;
        }
    }
}
