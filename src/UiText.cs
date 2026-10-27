using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Web.Script.Serialization;
using System.Windows.Forms;

namespace Tap2Trd {
    internal static class UiText {
        internal static string Language = "ru";
        static readonly Dictionary<string, string> English = ReadCatalog();
        static Dictionary<string, string> ReadCatalog() {
            using (var stream = typeof(UiText).Assembly.GetManifestResourceStream("ui.en.json"))
            using (var reader = new StreamReader(stream, Encoding.UTF8))
                return new JavaScriptSerializer().Deserialize<Dictionary<string, string>>(reader.ReadToEnd());
        }
        internal static string T(string text) {
            if (text == null || Language != "en") return text;
            string translated;
            if (English.TryGetValue(text, out translated)) return translated;
            return String.Join("\n", text.Split('\n').Select(part => English.TryGetValue(part, out translated) ? translated : part));
        }
        internal static string Source(string text) {
            foreach (var pair in English) if (pair.Value == text) return pair.Key;
            return text;
        }
        internal static string SettingsPath { get { return Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "settings.json"); } }
        internal static string ReadLanguage() {
            try {
                var settings = new JavaScriptSerializer().Deserialize<Dictionary<string, string>>(File.ReadAllText(SettingsPath));
                return settings != null && settings.ContainsKey("language") && settings["language"] == "en" ? "en" : "ru";
            } catch (IOException) { return "ru"; } catch (UnauthorizedAccessException) { return "ru"; }
              catch (ArgumentException) { return "ru"; } catch (InvalidOperationException) { return "ru"; }
        }
        internal static bool SaveLanguage() {
            try { File.WriteAllText(SettingsPath, "{\"language\":\"" + Language + "\"}", Encoding.UTF8); return true; }
            catch (IOException) { return false; } catch (UnauthorizedAccessException) { return false; }
        }
    }

}
