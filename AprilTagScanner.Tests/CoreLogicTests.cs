using AprilTagScanner.Models;
using AprilTagScanner.Services;
using OpenCvSharp;
using Xunit;

namespace AprilTagScanner.Tests;

public class ScanSessionTests
{
    private static DetectedTag Tag(string family, int id, float x = 10, float y = 10) =>
        new()
        {
            Family = family,
            Id = id,
            Corners =
            [
                new Point2f(x, y),
                new Point2f(x + 20, y),
                new Point2f(x + 20, y + 20),
                new Point2f(x, y + 20),
            ],
        };

    [Fact]
    public void FirstSight_RecordsOnce()
    {
        var session = new ScanSession();
        var a = Tag("tag36h11", 7);

        var added = session.ProcessDetections([a], missLimit: 8);
        Assert.Single(added);
        Assert.False(added[0].Duplicate);

        added = session.ProcessDetections([a], missLimit: 8);
        Assert.Empty(added);
        Assert.Single(session.Records);
    }

    [Fact]
    public void ReappearAfterOtherTag_IsDuplicate()
    {
        var session = new ScanSession();
        var a = Tag("tag36h11", 1, x: 10);
        var b = Tag("tag36h11", 2, x: 100);

        Assert.Single(session.ProcessDetections([a], 8));
        Assert.Single(session.ProcessDetections([a, b], 8));

        // Clear visibility so A is treated as a new entry.
        session.ClearTracking();
        var again = session.ProcessDetections([a], 8);
        Assert.Single(again);
        Assert.True(again[0].Duplicate);
        Assert.Contains(new TagKey("tag36h11", 1), session.Duplicates);
    }

    [Fact]
    public void FlickerWithinMissLimit_DoesNotRerecord()
    {
        var session = new ScanSession();
        var a = Tag("tag36h11", 3);

        session.ProcessDetections([a], missLimit: 3);
        // 2 misses — still tracked
        session.ProcessDetections([], missLimit: 3);
        session.ProcessDetections([], missLimit: 3);
        var added = session.ProcessDetections([a], missLimit: 3);
        Assert.Empty(added);
    }

    [Fact]
    public void MultiFamily_SameId_AreDistinctKeys()
    {
        var session = new ScanSession();
        var a = Tag("tag36h11", 5, x: 10);
        var b = Tag("tag25h9", 5, x: 80);

        var added = session.ProcessDetections([a, b], 8);
        Assert.Equal(2, added.Count);
        Assert.Equal(2, session.Records.Count);
    }
}

public class TagLabelsTests
{
    [Theory]
    [InlineData("tag36h11", 12, false, "12")]
    [InlineData("tag36h11", 12, true, "36h11:12")]
    [InlineData("36h11", 3, true, "36h11:3")]
    public void Format(string family, int id, bool include, string expected) =>
        Assert.Equal(expected, TagLabels.Format(family, id, include));

    [Fact]
    public void SessionNeedsFamily_WhenMixedOrMulti()
    {
        var mixed = new List<TagRecord>
        {
            new() { Family = "tag36h11", Id = 1 },
            new() { Family = "tag25h9", Id = 2 },
        };
        Assert.True(TagLabels.SessionNeedsFamily(mixed, multiFamily: false));
        Assert.True(TagLabels.SessionNeedsFamily([], multiFamily: true));
        Assert.False(TagLabels.SessionNeedsFamily(
            [new TagRecord { Family = "tag36h11", Id = 1 }],
            multiFamily: false));
    }
}

public class ScannedTagsImportTests
{
    [Fact]
    public void ParseCsv_ReadsFamilyAndId()
    {
        var path = Path.Combine(Path.GetTempPath(), $"ats_csv_{Guid.NewGuid():N}.csv");
        File.WriteAllText(path, """
            index,family,id,label,duplicate
            1,tag36h11,7,7,False
            2,tag25h9,3,25h9:3,False
            """);
        try
        {
            Assert.True(ScannedTagsImport.TryLoad(path, out var file, out var error), error);
            Assert.NotNull(file);
            Assert.Equal(2, file!.Tags.Count);
            Assert.Contains(new TagKey("tag36h11", 7), file.Tags);
            Assert.Contains(new TagKey("tag25h9", 3), file.Tags);
        }
        finally
        {
            File.Delete(path);
        }
    }

    [Fact]
    public void ParseTxt_FamilyPrefixedLine()
    {
        var path = Path.Combine(Path.GetTempPath(), $"ats_txt_{Guid.NewGuid():N}.txt");
        File.WriteAllText(path, """
            Families: 36h11
              1. 36h11:42
              2. 7
            """);
        try
        {
            Assert.True(ScannedTagsImport.TryLoad(path, out var file, out var error), error);
            Assert.NotNull(file);
            Assert.Contains(new TagKey("tag36h11", 42), file!.Tags);
            Assert.Contains(new TagKey("tag36h11", 7), file.Tags);
        }
        finally
        {
            File.Delete(path);
        }
    }
}
