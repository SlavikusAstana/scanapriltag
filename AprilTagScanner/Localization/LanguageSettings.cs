using System.Globalization;
using System.IO;
using System.Text.Json;

namespace AprilTagScanner.Localization;

public sealed class ScannerSettingsData
{
    public AppLanguage Language { get; set; } = AppLanguage.Russian;
    /// <summary>Not restored on startup — session always begins with auto-detect.</summary>
    public string Family { get; set; } = "tag36h11";
    public string Preset { get; set; } = "Balanced";
    /// <summary>Not restored on startup — same reason as Family.</summary>
    public bool MultiFamily { get; set; }
    public int MissLimit { get; set; } = 8;
    public bool BeepOnDuplicate { get; set; } = true;
    public int CameraIndex { get; set; }
    public string CameraName { get; set; } = "";
}

public static class LanguageSettings
{
    private static readonly string SettingsPath = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
        "AprilTagScanner",
        "settings.json");

    public static ScannerSettingsData LoadAll()
    {
        try
        {
            if (!File.Exists(SettingsPath))
                return new ScannerSettingsData { Language = DetectFromWindows() };

            var json = File.ReadAllText(SettingsPath);
            var data = JsonSerializer.Deserialize<ScannerSettingsData>(json);
            if (data == null)
                return new ScannerSettingsData { Language = DetectFromWindows() };
            if (data.MissLimit < 1)
                data.MissLimit = 8;
            return data;
        }
        catch
        {
            return new ScannerSettingsData { Language = DetectFromWindows() };
        }
    }

    public static AppLanguage Load() => LoadAll().Language;

    /// <summary>
    /// Uses the Windows display language. Falls back to English when UI is not Russian.
    /// </summary>
    public static AppLanguage DetectFromWindows()
    {
        var uiCulture = CultureInfo.CurrentUICulture;
        return uiCulture.TwoLetterISOLanguageName.Equals("ru", StringComparison.OrdinalIgnoreCase)
            ? AppLanguage.Russian
            : AppLanguage.English;
    }

    public static void Save(AppLanguage language)
    {
        var data = LoadAll();
        data.Language = language;
        Write(data);
    }

    public static void SaveAll(ScannerSettingsData data) => Write(data);

    private static void Write(ScannerSettingsData data)
    {
        try
        {
            var dir = Path.GetDirectoryName(SettingsPath)!;
            Directory.CreateDirectory(dir);
            var json = JsonSerializer.Serialize(data);
            File.WriteAllText(SettingsPath, json);
        }
        catch
        {
            // ignore persistence errors
        }
    }
}
