using System;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Reflection;
using System.Windows.Forms;

namespace Tap2Trd {
    internal partial class MainForm {
        readonly PictureBox brand = new LogoPictureBox();
        readonly Image russianLogo = ReadLogo("branding.ru");
        readonly Image englishLogo = ReadLogo("branding.en");
        readonly Icon applicationIcon = ReadIcon();

        static Image ReadLogo(string name) {
            using (var stream = Assembly.GetExecutingAssembly().GetManifestResourceStream(name))
            using (var source = Image.FromStream(stream)) return new Bitmap(source);
        }
        static Icon ReadIcon() {
            using (var stream = Assembly.GetExecutingAssembly().GetManifestResourceStream("branding.icon"))
            using (var source = new Icon(stream)) return (Icon)source.Clone();
        }
        Control BuildBranding() {
            var panel = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 2, RowCount = 1, Margin = Padding.Empty };
            panel.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
            panel.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 246));
            panel.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
            brand.Size = new Size(246, 164);
            brand.Dock = DockStyle.Fill; brand.Margin = Padding.Empty;
            brand.SizeMode = PictureBoxSizeMode.Zoom;
            brand.Image = russianLogo;
            brand.AccessibleName = "ТаРДулятор";
            brand.TabStop = false;
            panel.Controls.Add(BuildOptions(), 0, 0);
            panel.Controls.Add(brand, 1, 0);
            return panel;
        }
        protected override void Dispose(bool disposing) {
            if (disposing) brand.Image = null;
            base.Dispose(disposing);
            if (disposing) {
                russianLogo.Dispose(); englishLogo.Dispose(); applicationIcon.Dispose();
            }
        }
    }
    internal sealed class LogoPictureBox : PictureBox {
        protected override void OnPaint(PaintEventArgs e) {
            e.Graphics.InterpolationMode = InterpolationMode.HighQualityBicubic;
            e.Graphics.PixelOffsetMode = PixelOffsetMode.HighQuality;
            base.OnPaint(e);
        }
    }
}
