using AprilTagScanner.Localization;

namespace AprilTagScanner.Services;

public sealed class TagLayoutCalibration
{
    public float TagSizeMm { get; init; }
    public float? CenterSpacingHorizontalMm { get; init; }
    public float? CenterSpacingVerticalMm { get; init; }
    public float MarginTopMm { get; init; }
    public float MarginBottomMm { get; init; }
    public float MarginHorizontalMm { get; init; }
}

public static class TagLayoutSpec
{
    public const float A4WidthMm = 210f;
    public const float A4HeightMm = 297f;

    public const float SingleTagSizeMm = 185f;
    public const float SingleMarginTopMm = 20f;
    public const float SingleMarginBottomMm = 10f;
    public const float SingleMarginHorizontalMm = 10f;
    public const float SingleLabelGapMm = 8f;

    public const float GridTagSizeMm = 88f;
    public const float GridCenterSpacingMm = 94f;
    public const float GridMarginMm = 10f;
    public const int GridRows = 3;
    public const int GridCols = 2;

    public static float GridEdgeGapMm => GridCenterSpacingMm - GridTagSizeMm;

    public static TagLayoutCalibration GetCalibration(PageFormat format, int tagsPerPage)
    {
        _ = format;

        if (tagsPerPage == 1)
        {
            return new TagLayoutCalibration
            {
                TagSizeMm = SingleTagSizeMm,
                MarginTopMm = SingleMarginTopMm,
                MarginBottomMm = SingleMarginBottomMm,
                MarginHorizontalMm = SingleMarginHorizontalMm,
            };
        }

        return new TagLayoutCalibration
        {
            TagSizeMm = GridTagSizeMm,
            CenterSpacingHorizontalMm = GridCenterSpacingMm,
            CenterSpacingVerticalMm = GridCenterSpacingMm,
            MarginTopMm = GridMarginMm,
            MarginBottomMm = GridMarginMm,
            MarginHorizontalMm = GridMarginMm,
        };
    }

    public static string FormatCalibrationText(PageFormat format, int tagsPerPage)
    {
        var cal = GetCalibration(format, tagsPerPage);
        var pageName = format switch
        {
            PageFormat.A4 => "A4",
            _ => format.ToString(),
        };

        var lines = new List<string>
        {
            L.F("GenCalHeader", pageName),
            L.F("GenCalTagSize", Mm(cal.TagSizeMm), Mm(cal.TagSizeMm)),
        };

        if (tagsPerPage == 1)
        {
            lines.Add(L.F(
                "GenCalMarginsSingle",
                Mm(cal.MarginTopMm),
                Mm(cal.MarginBottomMm),
                Mm(cal.MarginHorizontalMm)));
        }
        else
        {
            lines.Add(L.F(
                "GenCalCenterSpacing",
                Mm(cal.CenterSpacingHorizontalMm!.Value),
                Mm(cal.CenterSpacingVerticalMm!.Value)));
            lines.Add(L.F("GenCalMarginsAll", Mm(cal.MarginHorizontalMm)));
        }

        lines.Add(L.S("GenCalPrintNote"));
        return string.Join(Environment.NewLine, lines);
    }

    private static string Mm(float value) =>
        value.ToString("0.##", System.Globalization.CultureInfo.InvariantCulture);
}
