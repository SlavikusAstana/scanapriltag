using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using OpenCvSharp;
using OpenCvSharp.Aruco;

const int tagId = 7;
const int renderSize = 256;
var outputPath = args.Length > 0
    ? args[0]
    : Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "AprilTagScanner", "Assets", "AppIcon.ico");
outputPath = Path.GetFullPath(outputPath);

Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(outputPath))!);

using var mat = RenderTag(tagId, renderSize);
using var source = MatToBitmap(mat);
SaveMultiSizeIcon(source, outputPath, [16, 32, 48, 64, 128, 256]);

Console.WriteLine($"Saved {Path.GetFullPath(outputPath)}");

static Mat RenderTag(int id, int pixelSize)
{
    var dict = CvAruco.GetPredefinedDictionary(PredefinedDictionaryName.DictAprilTag_36h11);
    var mat = new Mat();
    dict.GenerateImageMarker(id, pixelSize, mat, 1);

    var text = id.ToString();
    const HersheyFonts font = HersheyFonts.HersheySimplex;
    var fontScale = mat.Width / 937.5f;
    const int thickness = 2;
    var size = Cv2.GetTextSize(text, font, fontScale, thickness, out _);
    var margin = Math.Max(6, mat.Width / 64);
    var origin = new OpenCvSharp.Point(margin, margin + size.Height);

    Cv2.PutText(mat, text, origin, font, fontScale, Scalar.Black, thickness + 1, LineTypes.AntiAlias);
    Cv2.PutText(mat, text, origin, font, fontScale, Scalar.White, thickness, LineTypes.AntiAlias);
    return mat;
}

static Bitmap MatToBitmap(Mat mat)
{
    Cv2.ImEncode(".png", mat, out var png);
    using var ms = new MemoryStream(png);
    using var tmp = new Bitmap(ms);
    return new Bitmap(tmp);
}

static void SaveMultiSizeIcon(Bitmap source, string path, int[] sizes)
{
    using var stream = File.Create(path);
    using var writer = new BinaryWriter(stream);

    writer.Write((ushort)0);
    writer.Write((ushort)1);
    writer.Write((ushort)sizes.Length);

    var imageData = new List<byte[]>(sizes.Length);
    var offset = 6 + sizes.Length * 16;

    foreach (var size in sizes)
    {
        using var resized = ResizeBitmap(source, size);
        using var pngStream = new MemoryStream();
        resized.Save(pngStream, ImageFormat.Png);
        imageData.Add(pngStream.ToArray());
    }

    for (var i = 0; i < sizes.Length; i++)
    {
        var size = sizes[i];
        var data = imageData[i];
        writer.Write((byte)(size >= 256 ? 0 : size));
        writer.Write((byte)(size >= 256 ? 0 : size));
        writer.Write((byte)0);
        writer.Write((byte)0);
        writer.Write((ushort)1);
        writer.Write((ushort)32);
        writer.Write(data.Length);
        writer.Write(offset);
        offset += data.Length;
    }

    foreach (var data in imageData)
        writer.Write(data);
}

static Bitmap ResizeBitmap(Bitmap source, int size)
{
    var bmp = new Bitmap(size, size, PixelFormat.Format32bppArgb);
    using var g = Graphics.FromImage(bmp);
    g.Clear(Color.White);
    g.InterpolationMode = InterpolationMode.NearestNeighbor;
    g.PixelOffsetMode = PixelOffsetMode.Half;
    g.DrawImage(source, 0, 0, size, size);
    return bmp;
}
