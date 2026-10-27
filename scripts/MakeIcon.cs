using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.IO;

// Package the approved Russian artwork as a multi-resolution Windows icon.
internal static class MakeIcon {
    static byte[] Frame(Bitmap bitmap) {
        using (var stream = new MemoryStream()) {
            if (bitmap.Width == 256) bitmap.Save(stream, ImageFormat.Png);
            else using (var writer = new BinaryWriter(stream, System.Text.Encoding.UTF8, true)) {
                int size = bitmap.Width, maskStride = ((size + 31) / 32) * 4;
                writer.Write(40); writer.Write(size); writer.Write(size * 2);
                writer.Write((ushort)1); writer.Write((ushort)32); writer.Write(0);
                writer.Write(size * size * 4 + maskStride * size);
                for (int i = 0; i < 4; i++) writer.Write(0);
                for (int y = size - 1; y >= 0; y--)
                    for (int x = 0; x < size; x++) {
                        Color pixel = bitmap.GetPixel(x, y);
                        writer.Write(pixel.B); writer.Write(pixel.G); writer.Write(pixel.R); writer.Write(pixel.A);
                    }
                for (int y = size - 1; y >= 0; y--) {
                    var mask = new byte[maskStride];
                    for (int x = 0; x < size; x++)
                        if (bitmap.GetPixel(x, y).A == 0) mask[x / 8] |= (byte)(0x80 >> (x % 8));
                    writer.Write(mask);
                }
            }
            return stream.ToArray();
        }
    }
    static void Main(string[] args) {
        int[] sizes = { 16, 20, 24, 32, 40, 48, 64, 128, 256 };
        var frames = new List<byte[]>();
        using (var source = new Bitmap(args[0])) {
            int left = source.Width, top = source.Height, right = 0, bottom = 0;
            for (int y = 0; y < source.Height; y++)
                for (int x = 0; x < source.Width; x++)
                    if (source.GetPixel(x, y).A >= 32) {
                        left = Math.Min(left, x); top = Math.Min(top, y);
                        right = Math.Max(right, x + 1); bottom = Math.Max(bottom, y + 1);
                    }
            var bounds = Rectangle.FromLTRB(left, top, right, bottom);
            foreach (int size in sizes) using (var bitmap = new Bitmap(size, size, PixelFormat.Format32bppArgb)) {
                float scale = (float)(size - 2) / Math.Max(bounds.Width, bounds.Height);
                float width = bounds.Width * scale, height = bounds.Height * scale;
                using (var graphics = Graphics.FromImage(bitmap)) {
                    graphics.Clear(Color.Transparent);
                    graphics.InterpolationMode = InterpolationMode.HighQualityBicubic;
                    graphics.PixelOffsetMode = PixelOffsetMode.HighQuality;
                    graphics.DrawImage(source, new RectangleF((size - width) / 2, (size - height) / 2, width, height), bounds, GraphicsUnit.Pixel);
                }
                frames.Add(Frame(bitmap));
            }
        }
        using (var writer = new BinaryWriter(File.Create(args[1]))) {
            writer.Write((ushort)0); writer.Write((ushort)1); writer.Write((ushort)sizes.Length);
            int offset = 6 + sizes.Length * 16;
            for (int i = 0; i < sizes.Length; i++) {
                writer.Write((byte)(sizes[i] % 256)); writer.Write((byte)(sizes[i] % 256));
                writer.Write((byte)0); writer.Write((byte)0);
                writer.Write((ushort)1); writer.Write((ushort)32);
                writer.Write(frames[i].Length); writer.Write(offset);
                offset += frames[i].Length;
            }
            foreach (var frame in frames) writer.Write(frame);
        }
        Console.WriteLine("Icon: 9 sizes from 16 to 256 px.");
    }
}
