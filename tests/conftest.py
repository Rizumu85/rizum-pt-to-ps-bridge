from sp_plugin.rizum_sp_to_ps import localization

# The suite asserts English UI text, and the plugin takes its language from
# this machine's Painter preference. Pinned at import, before any test module
# builds a widget, so no test depends on how Painter is set up here.
localization.CURRENT_LANGUAGE = "en"
