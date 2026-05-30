using AprilTagScanner.Localization;
using OpenCvSharp.Aruco;

namespace AprilTagScanner.Services;

public static class TagFamilyCatalog
{
    public static IReadOnlyList<string> AllFamilies { get; } =
        ["tag36h11", "tag25h9", "tag16h5", "tag36h10"];

    public static IReadOnlyList<string> ProbePriority { get; } = AllFamilies;

    public static IReadOnlyList<string> MultiFamilies { get; } =
        ["tag36h11", "tag25h9", "tag16h5"];

    public static string GetLabel(string family) => L.FamilyLabel(family);

    public static PredefinedDictionaryName ToDictionary(string family) => family switch
    {
        "tag36h11" => PredefinedDictionaryName.DictAprilTag_36h11,
        "tag25h9" => PredefinedDictionaryName.DictAprilTag_25h9,
        "tag16h5" => PredefinedDictionaryName.DictAprilTag_16h5,
        "tag36h10" => PredefinedDictionaryName.DictAprilTag_36h10,
        _ => PredefinedDictionaryName.DictAprilTag_36h11,
    };
}

public enum SpeedPreset
{
    Fast,
    Balanced,
    Accurate,
}

public static class SpeedPresetSettings
{
    public static (int DetectWidth, float Decimate, int Stride) Get(SpeedPreset preset) =>
        preset switch
        {
            SpeedPreset.Fast => (640, 2.0f, 2),
            SpeedPreset.Balanced => (960, 1.5f, 1),
            _ => (1280, 1.0f, 1),
        };

    public static string Label(SpeedPreset preset) => preset switch
    {
        SpeedPreset.Fast => L.PresetFast,
        SpeedPreset.Balanced => L.PresetBalanced,
        _ => L.PresetAccurate,
    };
}
