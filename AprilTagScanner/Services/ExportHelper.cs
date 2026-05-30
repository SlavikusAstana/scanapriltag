using System.IO;

using System.Text;

using System.Text.Json;

using AprilTagScanner.Localization;

using AprilTagScanner.Models;



namespace AprilTagScanner.Services;



public static class ExportHelper

{

    public static string BuildTextReport(ScanSession session, string families, DateTime when)

    {

        var sb = new StringBuilder();

        sb.AppendLine(L.S("ExportTitle"));

        sb.AppendLine(L.F("ExportDate", when));

        sb.AppendLine();

        sb.AppendLine(L.F("ExportFamilies", families));



        if (session.Records.Count == 0)

        {

            sb.AppendLine(L.S("ExportEmpty"));

            return sb.ToString();

        }



        sb.AppendLine(L.F("ExportTotal", session.Records.Count));

        sb.AppendLine(L.F("ExportUnique", session.Records.Select(r => new TagKey(r.Family, r.Id)).Distinct().Count()));

        sb.AppendLine();



        for (var i = 0; i < session.Records.Count; i++)

        {

            var r = session.Records[i];

            var mark = r.Duplicate ? L.S("DuplicateMarkExport") : "";

            sb.AppendLine($"  {i + 1}. {r.Label}{mark}");

        }



        sb.AppendLine();

        if (session.Duplicates.Count > 0)

        {

            var dup = string.Join(", ", session.Duplicates.Select(k => k.Id.ToString()));

            sb.AppendLine(L.F("ExportDupYes", dup));

        }

        else

        {

            sb.AppendLine(L.S("ExportDupNo"));

        }



        return sb.ToString();

    }



    public static void Save(string path, ScanSession session, string families)

    {

        var ext = Path.GetExtension(path).ToLowerInvariant();

        var when = DateTime.Now;



        if (ext == ".json")

        {

            var payload = new

            {

                app = L.S("ExportTitle"),

                date = when,

                families,

                total = session.Records.Count,

                unique = session.Records.Select(r => new TagKey(r.Family, r.Id)).Distinct().Count(),

                duplicates = session.Duplicates.Select(d => new { family = d.Family, id = d.Id }),

                tags = session.Records.Select((r, i) => new

                {

                    index = i + 1,

                    family = r.Family,

                    id = r.Id,

                    label = r.Label,

                    duplicate = r.Duplicate,

                }),

            };

            File.WriteAllText(path, JsonSerializer.Serialize(payload, new JsonSerializerOptions { WriteIndented = true }), Encoding.UTF8);

            return;

        }



        if (ext == ".csv")

        {

            var sb = new StringBuilder();

            sb.AppendLine("index,family,id,label,duplicate");

            for (var i = 0; i < session.Records.Count; i++)

            {

                var r = session.Records[i];

                sb.AppendLine($"{i + 1},{r.Family},{r.Id},{r.Label},{r.Duplicate}");

            }



            File.WriteAllText(path, sb.ToString(), new UTF8Encoding(true));

            return;

        }



        File.WriteAllText(path, BuildTextReport(session, families, when), Encoding.UTF8);

    }

}


