using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Web.Script.Serialization;
using System.Windows.Forms;

namespace Tap2Trd {
    internal partial class MainForm {
        readonly Dictionary<Control, string> uiCaptions = new Dictionary<Control, string>();
        readonly Dictionary<Control, string> uiNames = new Dictionary<Control, string>();
        readonly Dictionary<DataGridViewColumn, string> uiColumns = new Dictionary<DataGridViewColumn, string>();
        readonly Dictionary<ComboBox, string[]> uiChoices = new Dictionary<ComboBox, string[]>();
        readonly RadioButton russianOption = new RadioButton(), englishOption = new RadioButton();
        readonly RadioButton collectionOption = new RadioButton(), directOption = new RadioButton();
        bool syncingOptions;
        bool directLaunch;
        Control menuEditor;

        void InitializeLanguage() {
            CaptureCaptions(this);
            foreach (DataGridViewColumn column in grid.Columns) uiColumns[column] = column.HeaderText;
            foreach (var combo in new[] { loadModel, transferMode, elementInk, elementPaper })
                uiChoices[combo] = combo.Items.Cast<object>().Select(Convert.ToString).ToArray();
            ChangeLanguage(UiText.ReadLanguage(), false);
        }
        Control BuildOptions() {
            var panel = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 1, RowCount = 4,
                Padding = new Padding(8, 8, 8, 0), Margin = Padding.Empty };
            foreach (int height in new[] { 24, 32, 24, 56 }) panel.RowStyles.Add(new RowStyle(SizeType.Absolute, height));
            var languageLabel = Label("Язык интерфейса", 9, muted); languageLabel.Margin = Padding.Empty;
            panel.Controls.Add(languageLabel, 0, 0);
            var languages = new FlowLayoutPanel { Dock = DockStyle.Fill, WrapContents = false, Margin = Padding.Empty };
            ConfigureOption(russianOption, "Русский"); ConfigureOption(englishOption, "English");
            languages.Controls.Add(russianOption); languages.Controls.Add(englishOption); panel.Controls.Add(languages, 0, 1);
            russianOption.CheckedChanged += delegate { SelectLanguage(russianOption, "ru"); };
            englishOption.CheckedChanged += delegate { SelectLanguage(englishOption, "en"); };
            var launchLabel = Label("Запуск дискеты", 9, muted); launchLabel.Margin = Padding.Empty;
            panel.Controls.Add(launchLabel, 0, 2);
            var launch = new FlowLayoutPanel { Dock = DockStyle.Fill, FlowDirection = FlowDirection.TopDown,
                WrapContents = false, Margin = Padding.Empty };
            ConfigureOption(collectionOption, "Меню сборника"); ConfigureOption(directOption, "Одна программа без меню");
            launch.Controls.Add(collectionOption); launch.Controls.Add(directOption); panel.Controls.Add(launch, 0, 3);
            collectionOption.CheckedChanged += delegate { if (!syncingOptions && collectionOption.Checked) SetLaunchMode(false); };
            directOption.CheckedChanged += delegate { if (!syncingOptions && directOption.Checked) SetLaunchMode(true); };
            return panel;
        }
        void ConfigureOption(RadioButton option, string text) {
            option.Text = text; option.AutoSize = true; option.UseVisualStyleBackColor = true;
            option.Margin = new Padding(0, 0, 12, 5); locked.Add(option);
        }
        void SelectLanguage(RadioButton option, string language) {
            if (syncingOptions || !option.Checked) return;
            ChangeLanguage(language, true);
            SyncOptions(); // A rejected cell edit must also restore the previous radio selection.
        }
        void SyncOptions() {
            syncingOptions = true;
            russianOption.Checked = UiText.Language == "ru"; englishOption.Checked = UiText.Language == "en";
            collectionOption.Checked = !directLaunch; directOption.Checked = directLaunch;
            syncingOptions = false;
        }
        void SetLaunchMode(bool direct) {
            if (busy) { SyncOptions(); return; }
            directLaunch = direct;
            SyncOptions();
            menuEditor.Enabled = !direct;
            UpdatePreview();
            status.Text = UiText.T(direct ? "Без меню: одна программа запускается сразу через RUN. Файлы загрузчика остаются на диске."
                : "Меню сборника включено. Расположение и надписи сохранены.");
        }
        void CaptureCaptions(Control parent) {
            foreach (Control control in parent.Controls) {
                if ((control is Label || control is ButtonBase || control is TabPage) &&
                    control != status && control != count && control != layoutWarning && control != gameDetails)
                    uiCaptions[control] = control.Text;
                if (!String.IsNullOrEmpty(control.AccessibleName)) uiNames[control] = control.AccessibleName;
                CaptureCaptions(control);
            }
        }
        void ChangeLanguage(string language, bool save) {
            if (busy || !grid.EndEdit()) return;
            UiText.Language = language;
            SuspendLayout();
            Text = UiText.T("ТаРДулятор") + " " + AppVersion.Value + " · " + UiText.T("сборник для Spectrum");
            brand.Image = language == "en" ? englishLogo : russianLogo;
            SyncOptions();
            foreach (var pair in uiCaptions) pair.Key.Text = UiText.T(pair.Value);
            foreach (var pair in uiNames) pair.Key.AccessibleName = UiText.T(pair.Value);
            foreach (var pair in uiColumns) pair.Key.HeaderText = UiText.T(pair.Value);
            syncingGame = syncingEditor = true;
            foreach (var pair in uiChoices) {
                int index = pair.Key.SelectedIndex;
                pair.Key.Items.Clear(); pair.Key.Items.AddRange(pair.Value.Select(UiText.T).ToArray());
                pair.Key.SelectedIndex = index;
            }
            int selected = elementChoice.SelectedIndex;
            elementChoice.Items.Clear();
            syncingGame = syncingEditor = false;
            foreach (DataGridViewRow row in grid.Rows) {
                row.Cells["State"].Value = UiText.T(UiText.Source(Convert.ToString(row.Cells["State"].Value)));
                if (row.Cells["Disk"].Tag != null) row.Cells["Disk"].ToolTipText = UiText.T("С загрузчиком и округлением до секторов по 256 байт.");
            }
            SyncGameOptions(); UpdatePreview();
            if (selected >= 0 && selected < elementChoice.Items.Count) elementChoice.SelectedIndex = selected;
            status.Text = UiText.T("Добавьте программы, выберите фон и создайте TRD.");
            string intro = "TAP и TZX: модель 48К/128К выбирается автоматически. Лимит загрузки — 20 минут времени Spectrum.\r\nПроизвольная подгрузка и запись на кассету не переносятся. После сборки проверьте запуск.";
            if (!save || UiText.Source(log.Text) == intro) log.Text = UiText.T(intro);
            if (save) {
                bool saved = UiText.SaveLanguage();
                status.Text = UiText.T(saved ? "Язык интерфейса сохранён. Надписи меню дискеты не изменены." : "Язык изменён для этого сеанса; не удалось записать settings.json.");
            }
            ResumeLayout(true);
        }
    }
}
