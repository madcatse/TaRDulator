using System;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.IO;
using System.Reflection;

namespace Tap2Trd {
    internal static class SpectrumScreen {
        internal static readonly Color[] Colors = MakePalette();
        static readonly byte[] Font = ReadFont();
        static byte[] ReadFont() {
            using (var s = Assembly.GetExecutingAssembly().GetManifestResourceStream("spectrum.font")) {
                byte[] b = new byte[1296];
                if (s == null || s.Read(b, 0, b.Length) != b.Length) throw new InvalidDataException(UiText.T("Не найден шрифт Spectrum"));
                return b;
            }
        }
        static Color[] MakePalette() {
            Color[] c = new Color[16];
            for (int i = 0; i < 16; i++) {
                int v = i < 8 ? 205 : 255;
                c[i] = Color.FromArgb((i & 2) != 0 ? v : 0, (i & 4) != 0 ? v : 0, (i & 1) != 0 ? v : 0);
            }
            return c;
        }
        static int Offset(int x, int y) { return (y / 64) * 2048 + (y % 8) * 256 + ((y / 8) % 8) * 32 + x / 8; }
        internal static string Text(string value, int length) {
            var b = new System.Text.StringBuilder();
            foreach (char c in value ?? "") b.Append(Supported(c) ? c : '?');
            string s = b.ToString().Trim();
            return s.Length > length ? s.Substring(0, length) : s;
        }
        internal static bool Supported(char c) { return c >= 32 && c <= 126 || c >= 'А' && c <= 'я' || c == 'Ё' || c == 'ё'; }
        static int Glyph(char c) { return c >= 'А' && c <= 'я' ? 96 + c - 'А' : c == 'Ё' ? 160 : c == 'ё' ? 161 : Supported(c) ? c - 32 : '?' - 32; }
        internal static byte[] DefaultBackground() {
            byte[] s = new byte[6912];
            for (int a = 6144; a < 6912; a++) s[a] = 1;
            int[] rainbow = { 2, 6, 4, 5, 1, 3 };
            for (int y = 0; y < 192; y++) for (int x = 0; x < 256; x++) {
                bool stripe = y >= 176 && x >= 160 && ((x + y) / 8) % 6 != 0;
                if (stripe || (x * 73 + y * 151) % 541 == 0) s[Offset(x, y)] |= (byte)(128 >> (x % 8));
                if (stripe) s[6144 + (y / 8) * 32 + x / 8] = (byte)(64 + rainbow[((x / 8) + (y / 8)) % 6]);
            }
            return s;
        }
        internal static void Print(byte[] s, int row, int col, string text, int ink, bool bright) {
            Print(s, new MenuElement { x = col, y = row, width = Math.Min(32-col, text.Length), ink = ink, bright = bright }, text);
        }
        internal static void Print(byte[] s, MenuElement element, string text) {
            if (!element.visible || element.y < 0 || element.y > 23) return;
            int row = element.y, col = element.x;
            text = Text(text, element.width).PadRight(element.width);
            for (int i = 0; i < text.Length && col + i < 32; i++) {
                if (col + i < 0) continue;
                char c = text[i];
                for (int y = 0; y < 8; y++) s[Offset((col + i) * 8, row * 8 + y)] = Font[Glyph(c) * 8 + y];
                s[6144 + row * 32 + col + i] = (byte)(element.ink + element.paper * 8 + (element.bright ? 64 : 0));
            }
        }
        internal static byte[] Compose(byte[] background, string title, string[] names, MenuLayout layout, int pageIndex = 0, int pageCount = 1) {
            byte[] screen = (byte[])background.Clone();
            Print(screen, layout.title, title);
            for (int i = 0; i < names.Length; i++) Print(screen, layout.items[i], "123456789ABCDEFG"[i] + "  " + Text(names[i], 29));
            Print(screen, layout.hint, layout.hint.text);
            if (pageCount > 1) foreach (var item in new[] { layout.previous, layout.next, layout.page })
                Print(screen, item, (item.text ?? "").Replace("{page}", (pageIndex+1).ToString()).Replace("{pages}", pageCount.ToString()));
            return screen;
        }
        internal static Bitmap Render(byte[] s) {
            if (s.Length != 6912) throw new InvalidDataException(UiText.T("SCR должен содержать 6912 байт"));
            Bitmap b = new Bitmap(256, 192);
            for (int y = 0; y < 192; y++) for (int x = 0; x < 256; x++) {
                int a = s[6144 + (y / 8) * 32 + x / 8];
                int color = (s[Offset(x, y)] & (128 >> (x % 8))) != 0 ? a & 7 : (a >> 3) & 7;
                b.SetPixel(x, y, Colors[color + ((a & 64) != 0 ? 8 : 0)]);
            }
            return b;
        }
        internal static byte[] ConvertImage(string path, bool dither) {
            if (Path.GetExtension(path).Equals(".scr", StringComparison.OrdinalIgnoreCase)) {
                var bytes = File.ReadAllBytes(path);
                if (bytes.Length != 6912) throw new InvalidDataException(UiText.T("SCR должен содержать ровно 6912 байт"));
                return bytes;
            }
            using (var original = Image.FromFile(path)) using (var b = new Bitmap(256, 192)) {
                using (var g = Graphics.FromImage(b)) {
                    g.Clear(Color.Black);
                    g.InterpolationMode = InterpolationMode.HighQualityBicubic;
                    float scale = Math.Max(256f / original.Width, 192f / original.Height);
                    float w = original.Width * scale, h = original.Height * scale;
                    g.DrawImage(original, (256 - w) / 2, (192 - h) / 2, w, h);
                }
                byte[] screen = new byte[6912];
                int[,] matrix = { {0,8,2,10}, {12,4,14,6}, {3,11,1,9}, {15,7,13,5} };
                for (int cy = 0; cy < 24; cy++) for (int cx = 0; cx < 32; cx++) {
                    Color[] pixels = new Color[64];
                    for (int j = 0; j < 64; j++) pixels[j] = b.GetPixel(cx * 8 + j % 8, cy * 8 + j / 8);
                    long best = long.MaxValue;
                    int bestInk = 0, bestPaper = 0, bestBright = 0;
                    for (int bright = 0; bright < 2; bright++) for (int paper = 0; paper < 8; paper++) for (int ink = paper; ink < 8; ink++) {
                        long error = 0;
                        foreach (Color p in pixels) error += Math.Min(Distance(p, Colors[paper + bright * 8]), Distance(p, Colors[ink + bright * 8]));
                        if (error < best) { best = error; bestInk = ink; bestPaper = paper; bestBright = bright; }
                    }
                    screen[6144 + cy * 32 + cx] = (byte)(bestInk + bestPaper * 8 + bestBright * 64);
                    for (int j = 0; j < 64; j++) {
                        int x = cx * 8 + j % 8, y = cy * 8 + j / 8;
                        Color p = pixels[j];
                        if (dither) {
                            int delta = (matrix[y % 4, x % 4] * 2 - 15) * 3;
                            p = Color.FromArgb(Clamp(p.R + delta), Clamp(p.G + delta), Clamp(p.B + delta));
                        }
                        if (Distance(p, Colors[bestInk + bestBright * 8]) < Distance(p, Colors[bestPaper + bestBright * 8]))
                            screen[Offset(x, y)] |= (byte)(128 >> (x % 8));
                    }
                }
                return screen;
            }
        }
        static int Clamp(int v) { return Math.Max(0, Math.Min(255, v)); }
        static int Distance(Color a, Color b) { int r = a.R - b.R, g = a.G - b.G, bl = a.B - b.B; return 2*r*r + 3*g*g + bl*bl; }
    }
    internal class PixelPreview : System.Windows.Forms.Control {
        Bitmap bitmap;
        internal MenuLayout Menu { get; set; }
        internal int ItemCount { get; set; }
        internal int Selected = -1;
        internal bool ShowGrid { get; set; }
        internal int PageCount { get; set; }
        internal Action<int> SelectElement { get; set; }
        internal Action<int, int, int> MoveElement { get; set; }
        bool dragging;
        Point grab;
        internal void ShowBitmap(Bitmap value) { var old = bitmap; bitmap = value; if (old != null) old.Dispose(); Invalidate(); }
        internal PixelPreview() { DoubleBuffered = true; BackColor = Color.Black; Cursor = System.Windows.Forms.Cursors.Hand; }
        Rectangle ImageBounds() {
            float scale = Math.Min(Width / 256f, Height / 192f);
            int w = Math.Max(1, (int)(256 * scale)), h = Math.Max(1, (int)(192 * scale));
            return new Rectangle((Width-w)/2, (Height-h)/2, w, h);
        }
        Point Cell(Point p) {
            var r = ImageBounds();
            return new Point((int)Math.Floor((p.X-r.X)*32.0/r.Width), (int)Math.Floor((p.Y-r.Y)*24.0/r.Height));
        }
        protected override void OnMouseDown(System.Windows.Forms.MouseEventArgs e) {
            base.OnMouseDown(e);
            if (e.Button != System.Windows.Forms.MouseButtons.Left || Menu == null || !ImageBounds().Contains(e.Location)) return;
            Point cell = Cell(e.Location);
            for (int i = ItemCount + MenuLayout.ItemOffset - 1; i >= 0; i--) {
                var s = Menu.At(i);
                if (Menu.Displayed(i, PageCount) && s.Bounds.Contains(cell)) {
                    Selected = i; grab = new Point(cell.X-s.x, cell.Y-s.y); dragging = true; Capture = true;
                    if (SelectElement != null) SelectElement(i); Invalidate(); return;
                }
            }
        }
        protected override void OnMouseMove(System.Windows.Forms.MouseEventArgs e) {
            base.OnMouseMove(e);
            if (!dragging || Selected < 0 || Menu == null) return;
            Point cell = Cell(e.Location); var s = Menu.At(Selected);
            if (MoveElement != null) MoveElement(Selected, Math.Max(0, Math.Min(32-s.width, cell.X-grab.X)), Math.Max(0, Math.Min(23, cell.Y-grab.Y)));
        }
        protected override void OnMouseUp(System.Windows.Forms.MouseEventArgs e) { base.OnMouseUp(e); dragging = false; Capture = false; }
        protected override void OnMouseCaptureChanged(EventArgs e) { base.OnMouseCaptureChanged(e); if (!Capture) dragging = false; }
        protected override void OnPaint(System.Windows.Forms.PaintEventArgs e) {
            base.OnPaint(e);
            if (bitmap == null) return;
            Rectangle r = ImageBounds();
            e.Graphics.InterpolationMode = InterpolationMode.NearestNeighbor;
            e.Graphics.PixelOffsetMode = PixelOffsetMode.Half;
            e.Graphics.DrawImage(bitmap, r);
            if (ShowGrid) using (var pen = new Pen(Color.FromArgb(65, Color.White))) {
                for (int x = 0; x <= 32; x++) e.Graphics.DrawLine(pen, r.X+x*r.Width/32f, r.Y, r.X+x*r.Width/32f, r.Bottom);
                for (int y = 0; y <= 24; y++) e.Graphics.DrawLine(pen, r.X, r.Y+y*r.Height/24f, r.Right, r.Y+y*r.Height/24f);
            }
            if (Menu != null && Selected >= 0 && Selected < ItemCount+MenuLayout.ItemOffset && Menu.Displayed(Selected, PageCount)) {
                var s = Menu.At(Selected);
                using (var pen = new Pen(Color.FromArgb(98, 230, 199), 1))
                    e.Graphics.DrawRectangle(pen, r.X+s.x*r.Width/32f-1, r.Y+s.y*r.Height/24f-1, s.width*r.Width/32f+1, r.Height/24f+1);
            }
        }
        protected override void Dispose(bool disposing) { if (disposing && bitmap != null) bitmap.Dispose(); base.Dispose(disposing); }
    }
}
