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
        ExportIds(path, family, ids, tagsPerPage, pageFormat);
    }

    public static void ExportIds(
        string path,
        string family,
        IReadOnlyList<int> ids,
        int tagsPerPage,
        PageFormat pageFormat)
    {
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
        return RenderFirstPagePreviewIds(family, ids, tagsPerPage, pageFormat);
    }

    public static byte[] RenderFirstPagePreviewIds(
        string family,
        IReadOnlyList<int> ids,
        int tagsPerPage,
        PageFormat pageFormat)
    {
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
            page.MarginTop(TagLayoutSpec.SingleMarginTopMm, Unit.Millimetre);
            page.MarginBottom(TagLayoutSpec.SingleMarginBottomMm, Unit.Millimetre);
            page.MarginHorizontal(TagLayoutSpec.SingleMarginHorizontalMm, Unit.Millimetre);
            return;
        }

        page.Margin(TagLayoutSpec.GridMarginMm, Unit.Millimetre);
    }

    private static void ComposePage(IContainer container, string family, IReadOnlyList<int> ids, int tagsPerPage, bool forPreview)
    {
        if (tagsPerPage == 1)
        {
            var id = ids[0];
            var png = RenderMarkerImage(family, id, tagsPerPage, forPreview);

            container.AlignTop().AlignCenter().Column(column =>
            {
                column.Item()
                    .Width(TagLayoutSpec.SingleTagSizeMm, Unit.Millimetre)
                    .Height(TagLayoutSpec.SingleTagSizeMm, Unit.Millimetre)
                    .Image(png)
                    .FitArea();

                column.Item()
                    .ExtendHorizontal()
                    .PaddingTop(TagLayoutSpec.SingleLabelGapMm, Unit.Millimetre)
                    .Text(text =>
                    {
                        text.AlignCenter();
                        text.Span(id.ToString()).FontSize(150).SemiBold().FontColor(Colors.Black);
                    });
            });
            return;
        }

        var edgeGapMm = TagLayoutSpec.GridEdgeGapMm;

        container.AlignTop().Column(column =>
        {
            for (var row = 0; row < TagLayoutSpec.GridRows; row++)
            {
                column.Item()
                    .PaddingBottom(row < TagLayoutSpec.GridRows - 1 ? edgeGapMm : 0, Unit.Millimetre)
                    .Row(rowLayout =>
                    {
                        rowLayout.RelativeItem();

                        for (var col = 0; col < TagLayoutSpec.GridCols; col++)
                        {
                            if (col > 0)
                            {
                                rowLayout.ConstantItem(edgeGapMm, Unit.Millimetre)
                                    .Height(TagLayoutSpec.GridTagSizeMm, Unit.Millimetre);
                            }

                            var index = row * TagLayoutSpec.GridCols + col;
                            if (index >= ids.Count)
                            {
                                rowLayout.ConstantItem(TagLayoutSpec.GridTagSizeMm, Unit.Millimetre)
                                    .Height(TagLayoutSpec.GridTagSizeMm, Unit.Millimetre);
                                continue;
                            }

                            var id = ids[index];
                            var png = RenderMarkerImage(family, id, tagsPerPage, forPreview);
                            rowLayout.ConstantItem(TagLayoutSpec.GridTagSizeMm, Unit.Millimetre)
                                .Height(TagLayoutSpec.GridTagSizeMm, Unit.Millimetre)
                                .Image(png)
                                .FitArea();
                        }

                        rowLayout.RelativeItem();
                    });
            }
        });
    }
}
