using System.Globalization;
using System.IO;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using AprilTagScanner.Localization;
using AprilTagScanner.Models;

namespace AprilTagScanner.Services;

public sealed class ScannedTagsFile
{
    public required string Path { get; init; }
    public required IReadOnlyList<TagKey> Tags { get; init; }

    public IReadOnlySet<int> GetIdsForFamily(string family) =>
        Tags.Where(t => t.Family == family).Select(t => t.Id).ToHashSet();
}

public static class ScannedTagsImport
{
    private static readonly Regex TxtLineRegex = new(
        @"^\s*\d+\.\s*(?:(?<family>(?:tag)?[A-Za-z0-9]+):)?(?<id>\d+)",
        RegexOptions.Compiled | RegexOptions.CultureInvariant);

    private static readonly Regex TxtFamiliesRegex = new(
        @"(?:Families|Семейства):\s*(.+)$",
        RegexOptions.Compiled | RegexOptions.IgnoreCase | RegexOptions.CultureInvariant);

    public static bool TryLoad(string path, out ScannedTagsFile? file, out string error)
    {
        file = null;
        error = "";

        if (string.IsNullOrWhiteSpace(path) || !File.Exists(path))
        {
            error = L.S("GenScanFileMissing");
            return false;
        }

        try
        {
            var ext = System.IO.Path.GetExtension(path).ToLowerInvariant();
            var tags = ext switch
            {
                ".json" => ParseJson(path),
                ".csv" => ParseCsv(path),
                _ => ParseText(path),
            };

            if (tags.Count == 0)
            {
                error = L.S("GenScanFileEmpty");
                return false;
            }

            file = new ScannedTagsFile
            {
                Path = path,
                Tags = tags,
            };
            return true;
        }
        catch (Exception ex)
        {
            error = L.F("GenScanFileReadFailed", ex.Message);
            return false;
        }
    }

    private static List<TagKey> ParseJson(string path)
    {
        using var stream = File.OpenRead(path);
        using var doc = JsonDocument.Parse(stream);
        if (!doc.RootElement.TryGetProperty("tags", out var tagsElement) ||
            tagsElement.ValueKind != JsonValueKind.Array)
        {
            return [];
        }

        var tags = new List<TagKey>();
        foreach (var item in tagsElement.EnumerateArray())
        {
            if (!item.TryGetProperty("family", out var familyProp) ||
                !item.TryGetProperty("id", out var idProp))
                continue;

            var family = familyProp.GetString();
            if (string.IsNullOrWhiteSpace(family) || !idProp.TryGetInt32(out var id))
                continue;

            tags.Add(new TagKey(family, id));
        }

        return tags;
    }

    private static List<TagKey> ParseCsv(string path)
    {
        var lines = File.ReadAllLines(path, Encoding.UTF8);
        if (lines.Length < 2)
            return [];

        var tags = new List<TagKey>();
        for (var i = 1; i < lines.Length; i++)
        {
            var parts = SplitCsvLine(lines[i]);
            if (parts.Length < 3)
                continue;

            if (!int.TryParse(parts[2], NumberStyles.Integer, CultureInfo.InvariantCulture, out var id))
                continue;

            var family = parts[1].Trim();
            if (family.Length == 0)
                continue;

            tags.Add(new TagKey(family, id));
        }

        return tags;
    }

    private static List<TagKey> ParseText(string path)
    {
        var lines = File.ReadAllLines(path, Encoding.UTF8);
        var familyHints = new List<string>();
        var tags = new List<TagKey>();

        foreach (var line in lines)
        {
            var familyMatch = TxtFamiliesRegex.Match(line);
            if (familyMatch.Success)
            {
                familyHints = familyMatch.Groups[1].Value
                    .Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
                    .Select(TagLabels.CanonicalFamily)
                    .Where(f => f.Length > 0)
                    .ToList();
                continue;
            }

            var match = TxtLineRegex.Match(line);
            if (!match.Success)
                continue;

            if (!int.TryParse(match.Groups["id"].Value, NumberStyles.Integer, CultureInfo.InvariantCulture, out var id))
                continue;

            var familyGroup = match.Groups["family"];
            string family;
            if (familyGroup.Success && familyGroup.Value.Length > 0)
            {
                family = TagLabels.CanonicalFamily(familyGroup.Value);
            }
            else if (familyHints.Count == 1)
            {
                family = familyHints[0];
            }
            else
            {
                continue;
            }

            tags.Add(new TagKey(family, id));
        }

        return tags;
    }

    private static string[] SplitCsvLine(string line)
    {
        var parts = new List<string>();
        var current = new StringBuilder();
        var inQuotes = false;

        foreach (var ch in line)
        {
            if (ch == '"')
            {
                inQuotes = !inQuotes;
                continue;
            }

            if (ch == ',' && !inQuotes)
            {
                parts.Add(current.ToString());
                current.Clear();
                continue;
            }

            current.Append(ch);
        }

        parts.Add(current.ToString());
        return parts.ToArray();
    }
}
