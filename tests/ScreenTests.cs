using System;
using System.Drawing;
using System.IO;
using System.Collections.Generic;
using System.Linq;
using System.Web.Script.Serialization;
using Tap2Trd;

internal static class ScreenTests {
    public class Vector {
        public string title { get; set; }
        public string[] games { get; set; }
        public MenuLayout layout { get; set; }
        public string expected { get; set; }
        public int pageIndex { get; set; }
        public int pageCount { get; set; }
    }
    static void Main() {
        Directory.CreateDirectory(".work");
        byte[] background = SpectrumScreen.DefaultBackground();
        File.WriteAllBytes(".work/csharp-background.scr", background);
        using (var expected = SpectrumScreen.Render(background)) {
            expected.Save(".work/screen-test.png", System.Drawing.Imaging.ImageFormat.Png);
            byte[] converted = SpectrumScreen.ConvertImage(".work/screen-test.png", false);
            using (var actual = SpectrumScreen.Render(converted)) {
                for (int y = 0; y < 192; y++) for (int x = 0; x < 256; x++)
                    if (actual.GetPixel(x,y) != expected.GetPixel(x,y)) throw new Exception("SCR -> PNG -> SCR changed a visible pixel");
            }
        }
        if (SpectrumScreen.ConvertImage(".work/csharp-background.scr", false).Length != 6912) throw new Exception("SCR import");
        File.WriteAllBytes(".work/invalid.scr", new byte[6911]);
        bool rejected = false;
        try { SpectrumScreen.ConvertImage(".work/invalid.scr", false); } catch (InvalidDataException) { rejected = true; }
        if (!rejected) throw new Exception("Invalid SCR accepted");
        var json = new JavaScriptSerializer();
        var vectors = json.Deserialize<List<Vector>>(File.ReadAllText(".work/menu-vectors.json"));
        foreach (var v in vectors) {
            if (v.layout.Validate(v.games.Length, true, v.pageCount) != null) throw new Exception("Valid vector rejected");
            byte[] actual = SpectrumScreen.Compose(background, v.title, v.games, v.layout, v.pageIndex, v.pageCount);
            if (!actual.SequenceEqual(File.ReadAllBytes(".work/"+v.expected))) throw new Exception("Python/C# mismatch: " + v.expected);
        }
        var invalid = MenuLayout.Default(2); invalid.items[1].y = invalid.items[0].y;
        if (invalid.Validate(2) == null) throw new Exception("Overlap accepted");
        invalid.items[1].x = Int32.MaxValue;
        if (invalid.Validate(2) == null) throw new Exception("Invalid coordinates accepted");
        for (int count = 0; count <= 16; count++) {
            var arranged = MenuLayout.Default(16); arranged.Arrange(count, true);
            if (arranged.Validate(16) != null) throw new Exception("Invalid two-column arrangement");
            if (count > 1 && arranged.items[(count+1)/2].x != 17) throw new Exception("Second column not used");
            arranged.Arrange(count, false);
            if (arranged.Validate(16) != null) throw new Exception("Invalid one-column arrangement");
        }
        var template = new MenuTemplate { version = 1, title = "Мои игры Ёё", layout = MenuLayout.Default(16), background = Convert.ToBase64String(background) };
        template.layout.title.visible = false; template.layout.hint.y = 23;
        template.layout.items[0].x = 0; template.layout.items[0].width = 32;
        var restored = json.Deserialize<MenuTemplate>(json.Serialize(template));
        var expectedTemplate = SpectrumScreen.Compose(background, template.title, new[] { "Съёмка" }, template.layout);
        var actualTemplate = SpectrumScreen.Compose(Convert.FromBase64String(restored.background), restored.title, new[] { "Съёмка" }, restored.layout);
        if (!actualTemplate.SequenceEqual(expectedTemplate)) throw new Exception("Template save/load changed the menu");
        var legacy = json.Deserialize<Dictionary<string, object>>(json.Serialize(template));
        var oldLayout = (Dictionary<string, object>)legacy["layout"]; oldLayout["version"] = 1;
        foreach (string key in new[] { "previous", "next", "page" }) oldLayout.Remove(key);
        legacy.Remove("pages");
        var migrated = json.Deserialize<MenuTemplate>(json.Serialize(legacy)).ReadPages();
        if (!SpectrumScreen.Compose(background, template.title, new[] { "Съёмка" }, migrated[0]).SequenceEqual(expectedTemplate))
            throw new Exception("Legacy template changed");
        var paged = new MenuTemplate { version = 2, title = "СТРАНИЦЫ", background = template.background,
            pages = new List<MenuLayout> { MenuLayout.Default(16), MenuLayout.Default(16), MenuLayout.Default(16) } };
        paged.pages[1].previous.y = 22; paged.pages[1].next.y = 22; paged.pages[1].items[0].x = 0;
        var pages = json.Deserialize<MenuTemplate>(json.Serialize(paged)).ReadPages();
        if (pages[0].previous.y != 23 || pages[1].previous.y != 22 || pages[2].items[0].x != 2)
            throw new Exception("Page layouts lost independence");
        for (int i = 0; i < pages.Count; i++) {
            string[] games = Enumerable.Repeat("Игра", i == 2 ? 1 : 16).ToArray();
            if (!SpectrumScreen.Compose(background, paged.title, games, paged.pages[i], i, 3)
                    .SequenceEqual(SpectrumScreen.Compose(background, paged.title, games, pages[i], i, 3)))
                throw new Exception("Paged template changed screen");
        }
        string[] names = { "Зевс", "Бильярд", "Диверсант", "Брюс Ли", "Джофар", "Это Spectrum", "Весна 2024", "Windows 91" };
        var sample = MenuLayout.Default(names.Length);
        for (int i = 0; i < names.Length; i++) sample.items[i].y = 4+i*2;
        byte[] menu = SpectrumScreen.Compose(background, "КОЛЛЕКЦИЯ ИГР", names, sample);
        File.WriteAllBytes(".work/russian-preview.scr", menu);
        using (var preview = SpectrumScreen.Render(menu)) preview.Save("output/menu-russian-preview.png", System.Drawing.Imaging.ImageFormat.Png);
        Console.WriteLine("Screen checks passed: image conversion, Cyrillic, 8 parity vectors, independent pages, legacy templates.");
    }
}
