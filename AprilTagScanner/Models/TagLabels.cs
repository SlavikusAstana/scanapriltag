namespace AprilTagScanner.Models;

public static class TagLabels
{
    public static string ShortFamily(string family)
    {
        if (string.IsNullOrWhiteSpace(family))
            return "";

        var trimmed = family.Trim();
        return trimmed.StartsWith("tag", StringComparison.OrdinalIgnoreCase)
            ? trimmed[3..]
            : trimmed;
    }

    public static string CanonicalFamily(string family)
    {
        var shortName = ShortFamily(family);
        return string.IsNullOrEmpty(shortName) ? "" : "tag" + shortName;
    }

    public static string Format(string family, int id, bool includeFamily) =>
        includeFamily ? $"{ShortFamily(family)}:{id}" : id.ToString();

    public static bool SessionNeedsFamily(IEnumerable<TagRecord> records, bool multiFamily) =>
        multiFamily || records.Select(r => r.Family).Distinct().Skip(1).Any();
}
