// Compatible Telegram scan/run entry; execution is importable.
import { runLegacyUi } from '../ui/framework/legacy-requirement-ui.mjs';
await runLegacyUi(...process.argv.slice(2));
