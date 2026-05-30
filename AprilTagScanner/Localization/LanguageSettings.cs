using System.Globalization;
using System.IO;
using System.Text.Json;

namespace AprilTagScanner.Localization;

public static class LanguageSettings
{
    private static readonly string SettingsPath = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
        "AprilTagScanner",
        "settings.json");

    public static AppLanguage Load()
    {
        try
        {
            if (!File.Exists(SettingsPath))
                return DetectFromWindows();

            var json = File.ReadAllText(SettingsPath);
            var data = JsonSerializer.Deserialize<SettingsData>(json);
            return data?.Language ?? DetectFromWindows();
        }
        catch
        {
            return DetectFromWindows();
        }
    }

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
        try
        {
            var dir = Path.GetDirectoryName(SettingsPath)!;
            Directory.CreateDirectory(dir);
            var json = JsonSerializer.Serialize(new SettingsData { Language = language });
            File.WriteAllText(SettingsPath, json);
        }
        catch
        {
            // ignore persistence errors
        }
    }

    private sealed class SettingsData
    {
        public AppLanguage Language { get; init; } = AppLanguage.Russian;
    }
}
