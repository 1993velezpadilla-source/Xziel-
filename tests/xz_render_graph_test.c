#include "../engine/xz/xz_render_graph.h"

#include <assert.h>
#include <stdio.h>
#include <string.h>

static void test_read_before_write(void)
{
    XzRenderGraph graph;
    XzRenderGraphCompiled compiled;
    XzRgResourceDesc resource;
    XzRgPassDesc pass;
    int transient;

    XzRenderGraph_Init(&graph);
    memset(&resource, 0, sizeof(resource));
    resource.width = 64u;
    resource.height = 64u;
    resource.format = XZ_RG_FORMAT_RGBA8;
    resource.flags = XZ_RG_RESOURCE_TRANSIENT;
    transient = XzRenderGraph_AddResource(
        &graph, &resource);
    assert(transient >= 0);

    memset(&pass, 0, sizeof(pass));
    pass.read_mask = 1u << (unsigned int)transient;
    assert(XzRenderGraph_AddPass(&graph, &pass) >= 0);

    assert(!XzRenderGraph_Compile(&graph, &compiled));
    assert(compiled.error ==
           XZ_RG_ERROR_READ_BEFORE_WRITE);
}

static void test_imported_read(void)
{
    XzRenderGraph graph;
    XzRenderGraphCompiled compiled;
    XzRgResourceDesc resource;
    XzRgPassDesc pass;
    int history;

    XzRenderGraph_Init(&graph);
    memset(&resource, 0, sizeof(resource));
    resource.width = 128u;
    resource.height = 128u;
    resource.format = XZ_RG_FORMAT_RGBA8;
    resource.flags =
        XZ_RG_RESOURCE_IMPORTED |
        XZ_RG_RESOURCE_PRESERVE;
    history = XzRenderGraph_AddResource(
        &graph, &resource);
    assert(history >= 0);

    memset(&pass, 0, sizeof(pass));
    pass.read_mask = 1u << (unsigned int)history;
    pass.flags = XZ_RG_PASS_NEEDS_HISTORY;
    assert(XzRenderGraph_AddPass(&graph, &pass) >= 0);

    assert(XzRenderGraph_Compile(&graph, &compiled));
    assert(compiled.valid);
    assert(compiled.alias_slot[history] < 0);
}

int main(void)
{
    assert(XzRenderGraph_SelfTest());
    test_read_before_write();
    test_imported_read();

    puts("xz_render_graph_test: PASS");
    return 0;
}
