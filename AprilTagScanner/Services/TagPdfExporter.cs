using QuestPDF.Fluent;
using QuestPDF.Helpers;
using QuestPDF.Infrastructure;

namespace AprilTagScanner.Services;

public enum PageFormat
{
    A4,
}

public static class TagPdfExporter
{
    public static void Export(
        string path,
        string family,
        int startId,
        int count,
        int tagsPerPage,
        PageFormat pageFormat)
    {
        var ids = TagGeneratorService.BuildIdSequence(startId, count);

        Document.Create(document =>
        {
            for (var offset = 0; offset < ids.Count; offset += tagsPerPage)
            {
                var pageIds = ids.Skip(offset).Take(tagsPerPage).ToList();
                document.Page(page =>
                {
                    ConfigurePage(page, pageFormat, tagsPerPage);
                    page.Content().Element(container => ComposePage(container, family, pageIds, tagsPerPage, forPreview: false));
                });
            }
        }).GeneratePdf(path);
    }

    public static byte[] RenderFirstPagePreview(
        string family,
        int startId,
        int count,
        int tagsPerPage,
        PageFormat pageFormat)
    {
        var ids = TagGeneratorService.BuildIdSequence(startId, count);
        var pageIds = ids.Take(tagsPerPage).ToList();

        return Document.Create(document =>
        {
            document.Page(page =>
            {
                ConfigurePage(page, pageFormat, tagsPerPage);
                page.Content().Element(container => ComposePage(container, family, pageIds, tagsPerPage, forPreview: true));
            });
        }).GenerateImages(new ImageGenerationSettings { RasterDpi = 96 }).First();
    }

    private static byte[] RenderMarkerImage(string family, int id, int tagsPerPage, bool forPreview)
    {
        var overlay = tagsPerPage == 6;
        if (forPreview)
        {
            return overlay
                ? TagGeneratorService.RenderMarkerPngWithOverlayPreview(family, id)
                : TagGeneratorService.RenderMarkerPngPreview(family, id);
        }

        return overlay
            ? TagGeneratorService.RenderMarkerPngWithOverlay(family, id)
            : TagGeneratorService.RenderMarkerPng(family, id);
    }

    private static PageSize ToPageSize(PageFormat format) =>
        format switch
        {
            PageFormat.A4 => PageSizes.A4,
            _ => PageSizes.A4,
        };

    private static void ConfigurePage(PageDescriptor page, PageFormat pageFormat, int tagsPerPage)
    {
        page.Size(ToPageSize(pageFormat));

        if (tagsPerPage == 1)
        {
            page.MarginTop(20, Unit.Millimetre);
            page.MarginBottom(10, Unit.Millimetre);
            page.MarginHorizontal(10, Unit.Millimetre);
            return;
        }

        page.Margin(10, Unit.Millimetre);
    }

    private static void ComposePage(IContainer container, string family, IReadOnlyList<int> ids, int tagsPerPage, bool forPreview)
    {
        if (tagsPerPage == 1)
        {
            var id = ids[0];
            var png = RenderMarkerImage(family, id, tagsPerPage, forPreview);
            const float tagSizeMm = 185f;

            container.AlignTop().AlignCenter().Column(column =>
            {
                column.Item()
                    .Width(tagSizeMm, Unit.Millimetre)
                    .Height(tagSizeMm, Unit.Millimetre)
                    .Image(png)
                    .FitArea();

                column.Item()
                    .ExtendHorizontal()
                    .PaddingTop(8, Unit.Millimetre)
                    .Text(text =>
                    {
                        text.AlignCenter();
                        text.Span(id.ToString()).FontSize(150).SemiBold().FontColor(Colors.Black);
                    });
            });
            return;
        }

        container.AlignTop().Column(column =>
        {
            const float tagSizeMm = 88f;
            const float rowGapMm = 6f;

            for (var row = 0; row < 3; row++)
            {
                column.Item()
                    .PaddingBottom(row < 2 ? rowGapMm : 0, Unit.Millimetre)
                    .Row(rowLayout =>
                    {
                        for (var col = 0; col < 2; col++)
                        {
                            var index = row * 2 + col;
                            if (index >= ids.Count)
                            {
                                rowLayout.RelativeItem();
                                continue;
                            }

                            var id = ids[index];
                            var png = RenderMarkerImage(family, id, tagsPerPage, forPreview);
                            rowLayout.RelativeItem().AlignCenter()
                                .Width(tagSizeMm, Unit.Millimetre)
                                .Height(tagSizeMm, Unit.Millimetre)
                                .Image(png)
                                .FitArea();
                        }
                    });
            }
        });
    }
}
