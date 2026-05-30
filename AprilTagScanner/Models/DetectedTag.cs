using OpenCvSharp;

namespace AprilTagScanner.Models;

public sealed class DetectedTag
{
    public required string Family { get; init; }
    public required int Id { get; init; }
    public required Point2f[] Corners { get; init; }

    public Point2f Center =>
        new(
            Corners.Average(p => p.X),
            Corners.Average(p => p.Y)
        );

    public TagKey Key => new(Family, Id);
}

public readonly record struct TagKey(string Family, int Id);

public sealed class TagRecord
{
    public required string Family { get; init; }
    public required int Id { get; init; }
    public bool Duplicate { get; set; }

    public string Label => Id.ToString();
}
