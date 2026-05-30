using OpenCvSharp;
using OpenCvSharp.Aruco;
using AprilTagScanner.Localization;

namespace AprilTagScanner.Services;

public static class TagGeneratorService
{
    public const int MarkerRenderPixels = 640;
    public const int PreviewRenderPixels = 400;

    public static int GetMarkerCount(string family)
    {
        var dict = CvAruco.GetPredefinedDictionary(TagFamilyCatalog.ToDictionary(family));
        return dict.BytesList.Rows;
    }

    public static int GetMaxId(string family) => GetMarkerCount(family) - 1;

    public static string FormatIdRange(string family) => $"0 … {GetMaxId(family)}";

    public static byte[] RenderMarkerPng(string family, int id) =>
        RenderMarkerPng(family, id, overlayId: false, pixelSize: MarkerRenderPixels);

    public static byte[] RenderMarkerPngWithOverlay(string family, int id) =>
        RenderMarkerPng(family, id, overlayId: true, pixelSize: MarkerRenderPixels);

    public static byte[] RenderMarkerPngPreview(string family, int id) =>
        RenderMarkerPng(family, id, overlayId: false, pixelSize: PreviewRenderPixels);

    public static byte[] RenderMarkerPngWithOverlayPreview(string family, int id) =>
        RenderMarkerPng(family, id, overlayId: true, pixelSize: PreviewRenderPixels);

    private static byte[] RenderMarkerPng(string family, int id, bool overlayId, int pixelSize)
    {
        var dict = CvAruco.GetPredefinedDictionary(TagFamilyCatalog.ToDictionary(family));
        using var mat = new Mat();
        dict.GenerateImageMarker(id, pixelSize, mat, 1);

        if (overlayId)
            DrawOverlayLabel(mat, id);

        Cv2.ImEncode(".png", mat, out var bytes);
        return bytes;
    }

    private static void DrawOverlayLabel(Mat mat, int id)
    {
        var text = id.ToString();
        const HersheyFonts font = HersheyFonts.HersheySimplex;
        var fontScale = mat.Width / 937.5f;
        var thickness = 2;
        var size = Cv2.GetTextSize(text, font, fontScale, thickness, out _);
        var margin = Math.Max(6, mat.Width / 64);
        var origin = new Point(margin, margin + size.Height);

        Cv2.PutText(mat, text, origin, font, fontScale, Scalar.Black, thickness + 1, LineTypes.AntiAlias);
        Cv2.PutText(mat, text, origin, font, fontScale, Scalar.White, thickness, LineTypes.AntiAlias);
    }

    public static bool TryValidate(string family, int startId, int count, out string error)
    {
        error = "";
        if (count < 1)
        {
            error = L.S("ValCountMin");
            return false;
        }

        if (startId < 0)
        {
            error = L.S("ValStartIdNegative");
            return false;
        }

        var maxId = GetMarkerCount(family) - 1;
        if (startId > maxId)
        {
            error = L.F("ValStartIdTooBigFamily", TagFamilyCatalog.GetLabel(family), maxId);
            return false;
        }

        var lastId = startId + count - 1;
        if (lastId > maxId)
        {
            error = L.F("ValRangeDict", lastId, maxId);
            return false;
        }

        return true;
    }

    public static IReadOnlyList<int> BuildIdSequence(int startId, int count) =>
        Enumerable.Range(startId, count).ToArray();
}
