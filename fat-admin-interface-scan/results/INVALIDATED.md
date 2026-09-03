# Invalidated bundle-route probe

The files prefixed `invalidated-bundle-route-` are an early diagnostic probe, not final interface-discovery evidence.

They visited routes extracted from the FAT bundle before reconciling those candidates with the rendered sidebar menu, and the probe clicked globally discovered tabs. They must not be merged into the final page/action/interface inventory or used to classify interfaces as ACTIVE, STALE, or REPLACED_BY.

The authoritative scan starts with `fat-admin-live-menu.json` and `fat-admin-live-menu-pages.csv`, then proceeds through page initialization and explicit per-page actions.
