using System;
using System.Linq;
using System.Windows.Forms;

namespace Tap2Trd {
    internal partial class MainForm {
        internal void CheckWindowLayout() {
            // Check the actual controls in an off-screen container. Form bounds are
            // clamped to the desktop on small CI monitors, even for hidden forms.
            var content = Controls.Cast<Control>().ToArray();
            var border = new System.Drawing.Size(Width - ClientSize.Width, Height - ClientSize.Height);
            using (var host = new Panel()) {
                try {
                    foreach (var control in content) host.Controls.Add(control);
                    foreach (var size in new[] {
                        new System.Drawing.Size(1220 + border.Width, 900 + border.Height),
                        new System.Drawing.Size(1160, 820),
                        new System.Drawing.Size(1440, 1000)
                    }) {
                        var client = new System.Drawing.Size(size.Width - border.Width, size.Height - border.Height);
                        host.Size = client; host.PerformLayout();
                        if (host.Size != client) throw new Exception("Test container size was constrained");
                        if (grid.Height < 200 || log.Height < 110 || preview.Height < 120)
                            throw new Exception("Content too small at " + size + ": grid=" + grid.Height + ", log=" + log.Height + ", preview=" + preview.Height);
                        if (grid.Parent != log.Parent || log.Top <= grid.Bottom || brand.Image == null || Icon == null)
                            throw new Exception("Branding or left-column log missing");
                        foreach (string language in new[] { "en", "ru" }) {
                            ChangeLanguage(language, false); host.PerformLayout();
                            if (directOption.Right > directOption.Parent.ClientSize.Width || directOption.Bottom > directOption.Parent.ClientSize.Height ||
                                englishOption.Right > englishOption.Parent.ClientSize.Width || showOutput.Right >= help.Left)
                                throw new Exception("Options or footer clipped at " + size + " in " + language);
                        }
                        Console.WriteLine("PASS: layout at " + size + ": grid=" + grid.Height + ", log=" + log.Height + ", preview=" + preview.Height);
                    }
                }
                finally {
                    foreach (var control in content) Controls.Add(control);
                }
            }
        }
        internal void CheckLanguageSwitch() {
            for (int i = 0; i < 20; i++) {
                int row = grid.Rows.Add("Игра " + i, "128", "33025", UiText.T("Готово"), "10", "128", "45", "preserve");
                grid.Rows[row].Tag = "C:\\Tapes\\Игра " + i + ".tap";
            }
            UpdatePreview(); grid.CurrentCell = grid.Rows[18].Cells[0];
            menuPages[1].items[2].x = 3; menuPages[1].items[2].width = 25;
            menuPages[1].hint.text = "МОЯ ПОДСКАЗКА";
            title.Text = "МОЙ СБОРНИК";
            elementChoice.SelectedIndex = 2;
            string before = json.Serialize(menuPages), titles = String.Join("|", grid.Rows.Cast<DataGridViewRow>().Select(r => r.Cells[0].Value));
            foreach (string language in new[] { "en", "ru", "en", "ru" }) {
                (language == "en" ? englishOption : russianOption).Checked = true;
                if (json.Serialize(menuPages) != before || previewPage != 1 || grid.CurrentRow.Index != 18 || elementChoice.SelectedIndex != 2)
                    throw new Exception("Language switch changed menu layout or selection: layout=" + (json.Serialize(menuPages) == before) + ", page=" + previewPage + ", row=" + grid.CurrentRow.Index + ", element=" + elementChoice.SelectedIndex);
                if (String.Join("|", grid.Rows.Cast<DataGridViewRow>().Select(r => r.Cells[0].Value)) != titles || title.Text != "МОЙ СБОРНИК")
                    throw new Exception("Language switch changed user text");
                if (Convert.ToString(grid.Rows[18].Cells["Model"].Value) != "128" || Convert.ToString(grid.Rows[18].Cells["Transfer"].Value) != "preserve" || startAddress.Text != "33025")
                    throw new Exception("Language switch changed load options");
                if (brand.AccessibleName != (language == "en" ? "TaRDulator" : "ТаРДулятор") ||
                    brand.Image != (language == "en" ? englishLogo : russianLogo) ||
                    englishOption.Checked != (language == "en") || russianOption.Checked != (language == "ru") ||
                    help.Text != (language == "en" ? "Help" : "Помощь") || !HelpPath.EndsWith("index." + language + ".html"))
                    throw new Exception("Brand or options were not translated");
                if (grid.Columns["Tape"].HeaderText != (language == "en" ? "File\nKiB" : "Файл\nКиБ"))
                    throw new Exception("Column header was not translated");
            }
            Console.WriteLine("PASS: RU/EN round trips preserve two pages, titles, selection and load options.");
            directOption.Checked = true; englishOption.Checked = true;
            if (!directLaunch || menuEditor.Enabled || !directOption.Checked || collectionOption.Checked ||
                directOption.Text != "One program without a menu") throw new Exception("Direct mode or translation lost");
            SetBusy(true);
            if (englishOption.Enabled || directOption.Enabled || !help.Enabled) throw new Exception("Busy options/help state incorrect");
            SetBusy(false);
            collectionOption.Checked = true; russianOption.Checked = true;
            if (!menuEditor.Enabled || json.Serialize(menuPages) != before)
                throw new Exception("Switching launch mode changed menu layout");
            Console.WriteLine("PASS: direct startup and language switching preserve collection layouts.");
            if (MainMenuStrip != null) throw new Exception("Old menu strip remains");
            OnEvent(new System.Collections.Generic.Dictionary<string, object> {
                {"event", "game_error"}, {"index", 18}, {"unsupported", true}, {"message", "Unresolved last block"}
            });
            if (Convert.ToString(grid.Rows[18].Cells["State"].Value) != "Не поддерживается" ||
                grid.Rows[18].Cells["State"].ToolTipText != "Unresolved last block")
                throw new Exception("Unsupported tape must have an explicit row status and reason");
            ChangeLanguage("en", false);
            if (Convert.ToString(grid.Rows[18].Cells["State"].Value) != "Unsupported")
                throw new Exception("Unsupported status was not translated");
            ChangeLanguage("ru", false);
            Console.WriteLine("PASS: unsupported tape status and reason are visible, with RU/EN translation.");
        }
    }
    internal static class UiTests {
        [STAThread] static void Main() {
            Application.EnableVisualStyles();
            using (var form = new MainForm(new string[0])) {
                form.CheckLanguageSwitch(); form.CheckWindowLayout();
            }
        }
    }
}
