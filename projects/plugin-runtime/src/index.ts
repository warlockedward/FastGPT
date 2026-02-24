import PluginRuntime from './manager';

const port = parseInt(process.env.PORT || '3001', 10);
const runtime = new PluginRuntime();
runtime.start(port);
