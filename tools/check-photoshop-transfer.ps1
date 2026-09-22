$ErrorActionPreference = 'Stop'
$root = Join-Path ([IO.Path]::GetTempPath()) ('pt-bridge-transfer-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $root | Out-Null
$ps = New-Object -ComObject Photoshop.Application
$previousId = $ps.DoJavaScript('app.documents.length ? String(app.activeDocument.id) : "";')
$rootJson = ConvertTo-Json $root -Compress
$setup = @'
(function (root) {
    var previous = app.documents.length ? app.activeDocument : null;
    var image = app.documents.add(64, 64, 72, "PT Bridge test pixels", NewDocumentMode.RGB, DocumentFill.TRANSPARENT);
    try {
        var color = new SolidColor(); color.rgb.hexValue = "80C0E0";
        image.selection.selectAll(); image.selection.fill(color); image.selection.deselect();
        image.saveAs(File(root + "/source.png"), new PNGSaveOptions(), true, Extension.LOWERCASE);
    } finally { image.close(SaveOptions.DONOTSAVECHANGES); }
    var doc = app.documents.add(64, 64, 72, "PT Bridge transfer fixture", NewDocumentMode.RGB, DocumentFill.TRANSPARENT);
    var base = doc.activeLayer; base.name = "Anchor";
    var group = doc.layerSets.add(); group.name = "Group";
    var child = doc.artLayers.add(); child.name = "Existing"; child.move(group, ElementPlacement.PLACEATBEGINNING);
    doc.saveAs(File(root + "/fixture.psd"), new PhotoshopSaveOptions(), false, Extension.LOWERCASE);
    var result = doc.id + "|" + base.id + "|" + group.id;
    if (previous) app.activeDocument = previous;
    return result;
}(__ROOT__));
'@
$ids = $ps.DoJavaScript($setup.Replace('__ROOT__', $rootJson)).Split('|')
$fixtureId = $ids[0]
$requestPath = Join-Path $root 'photoshop_transfer.json'
$fixturePath = Join-Path $root 'fixture.psd'
try {
    $layers = @(
        @{name='After A'; target_layer_id=[int]$ids[1]; insertion='after'; opacity=65},
        @{name='After B'; target_layer_id=[int]$ids[1]; insertion='after'; opacity=0.5},
        @{name='Inside C'; target_layer_id=[int]$ids[2]; insertion='inside'; opacity=100},
        @{name='Inside D'; target_layer_id=[int]$ids[2]; insertion='inside'; opacity=100}
    )
    foreach ($layer in $layers) {
        $layer.png = Join-Path $root 'source.png'
        $layer.blend_mode = 'NORMAL'
        $layer.visible = $true
    }
    # The wrong session ID proves the saved path takes precedence, without ever
    # changing the user's open document. All destination IDs belong to the fixture.
    $request = @{
        schema_version=1; request_type='painter_to_photoshop_transfer'
        document=@{id=$previousId; path=$fixturePath}; layers=$layers
    }
    $request | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $requestPath -Encoding utf8
    $launcher = python -c 'import sys; from sp_plugin.rizum_sp_to_ps.photoshop_automation import write_photoshop_transfer_launcher; print(write_photoshop_transfer_launcher(sys.argv[1]).launcher_path)' $requestPath
    if ($LASTEXITCODE -ne 0) { throw 'Could not generate transfer launcher' }
    $ps.DoJavaScriptFile($launcher) | Out-Null
    $result = Get-Content -LiteralPath (Join-Path $root 'photoshop_transfer_result.json') -Raw | ConvertFrom-Json
    if (!$result.success -or !$result.saved -or $result.inserted.Count -ne 4) { throw ($result | ConvertTo-Json -Depth 6) }
    $inspect = @'
(function (id) {
    var doc = null;
    for (var i = 0; i < app.documents.length; i++) if (app.documents[i].id == id) doc = app.documents[i];
    if (!doc) throw new Error("Fixture document not found");
    var names = []; var children = []; var opacity = null;
    for (var j = 0; j < doc.layers.length; j++) {
        var layer = doc.layers[j]; names.push(layer.name);
        if (layer.name === "After B") opacity = layer.opacity;
        if (layer.typename === "LayerSet") for (var k = 0; k < layer.layers.length; k++) children.push(layer.layers[k].name);
    }
    return names.join(",") + "|" + children.join(",") + "|" + opacity;
}(__ID__));
'@
    $actual = $ps.DoJavaScript($inspect.Replace('__ID__', $fixtureId))
    $parts = $actual.Split('|')
    # Photoshop stores opacity in 255 steps, so sub-percent values are quantized.
    if ($parts[0] -ne 'Group,Anchor,After B,After A' -or $parts[1] -ne 'Existing,Inside C,Inside D' -or [Math]::Abs([double]$parts[2] - 0.5) -gt (100.0 / 255)) {
        throw "Unexpected layer placement or opacity: $actual"
    }

    $request.layers = @($layers[0], @{name='Stale'; png=$layers[0].png; target_layer_id=2147483000; insertion='after'})
    $request | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $requestPath -Encoding utf8
    $launcher = python -c 'import sys; from sp_plugin.rizum_sp_to_ps.photoshop_automation import write_photoshop_transfer_launcher; print(write_photoshop_transfer_launcher(sys.argv[1]).launcher_path)' $requestPath
    if ($LASTEXITCODE -ne 0) { throw 'Could not generate preflight launcher' }
    $ps.DoJavaScriptFile($launcher) | Out-Null
    $rejected = Get-Content -LiteralPath (Join-Path $root 'photoshop_transfer_result.json') -Raw | ConvertFrom-Json
    if ($rejected.success -or $rejected.inserted.Count -ne 0) { throw 'Stale batch was not rejected before mutation' }
    if ($ps.DoJavaScript($inspect.Replace('__ID__', $fixtureId)) -ne $actual) { throw 'Preflight failure mutated the fixture' }
    Write-Output "PASS: path identity, insertion order, 0.5% opacity, save receipt, stale-target preflight. Artifacts: $root"
} finally {
    $cleanup = @'
(function (id, previous) {
    for (var i = app.documents.length - 1; i >= 0; i--) {
        if (app.documents[i].id == id) app.documents[i].close(SaveOptions.DONOTSAVECHANGES);
    }
    for (var j = 0; j < app.documents.length; j++) if (app.documents[j].id == previous) app.activeDocument = app.documents[j];
}(__ID__, __PREVIOUS__));
'@
    $ps.DoJavaScript($cleanup.Replace('__ID__', $fixtureId).Replace('__PREVIOUS__', (ConvertTo-Json $previousId -Compress))) | Out-Null
}
