# Build282 — inventory and market

User authorized all four notes on 13 November 2026; resumed 14 November.

- Rebind the inventory screen to the current authoritative native inventory vector after server refresh; preserve handles and quantities. Refresh the selected item's cached details after updates.
- Newly acquired items or increased stacks move to the first slot while the chest stays open. Reopening groups equipment/costumes, gems, stones, recipes and other materials.
- Render the market stock with the native chest's dimensions, icon sizes, quantity position and shared equipment upgrade painter.
- Use the in-game bottom input panel and a native iOS input dialog. Quantity, lot price and secondary password are separate steps; cancel, erase, validation, masking and pending mutation handling are retained.

Status: device framework compiled and Apple code-sign verification passed. Compiled ARM64 tests passed for six variants and 600 updates; native UIKit simulator quantity/price/password/cancel checks passed. Stock selection/grouping and interface regression checks passed (CI 43516974227 and UI 43517774030). Visual review now waits for a canvas redraw before capturing each input stage. The price label uses the native bitmap font's supported x separator. No claim of physical iPhone or live server testing. Base: supplied Build281 IPA; game executable and server remain the supplied versions.

Regression: returning from the recipe child screen preserves the current chest session, so the crafted result is promoted before grouping on an explicit close/reopen. Parent offset +0x10 is verified at native Z5.i 0x58a1a0.
