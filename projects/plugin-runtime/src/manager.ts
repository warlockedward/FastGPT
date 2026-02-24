import express, { Express, Request, Response } from 'express';
import { spawn, ChildProcess } from 'child_process';
import { v4 as uuidv4 } from 'uuid';
import * as fs from 'fs';
import * as path from 'path';

interface Plugin {
  id: string;
  name: string;
  code: string;
  language: 'typescript' | 'python';
  port?: number;
  process?: ChildProcess;
  status: 'starting' | 'running' | 'stopped' | 'error';
  healthCheck?: NodeJS.Timeout;
}

class PluginRuntime {
  private plugins: Map<string, Plugin> = new Map();
  private basePort: number = 3001;
  private app: Express;

  constructor() {
    this.app = express();
    this.app.use(express.json());
    this.setupRoutes();
  }

  private setupRoutes() {
    this.app.get('/health', (_req: Request, res: Response) => {
      res.json({ status: 'ok', plugins: this.plugins.size });
    });

    this.app.get('/plugins', (_req: Request, res: Response) => {
      const plugins = Array.from(this.plugins.values()).map((p) => ({
        id: p.id,
        name: p.name,
        status: p.status,
        port: p.port
      }));
      res.json(plugins);
    });

    this.app.post('/plugins', async (req: Request, res: Response) => {
      try {
        const { name, code, language, inputs } = req.body;

        if (!name || !code) {
          return res.status(400).json({ error: 'name and code are required' });
        }

        const pluginId = uuidv4();
        const port = this.basePort + this.plugins.size;

        const pluginDir = path.join(__dirname, 'plugins', pluginId);
        fs.mkdirSync(pluginDir, { recursive: true });

        const ext = language === 'python' ? 'py' : 'ts';
        fs.writeFileSync(path.join(pluginDir, `plugin.${ext}`), code);

        const plugin: Plugin = {
          id: pluginId,
          name,
          code,
          language: language || 'typescript',
          port,
          status: 'starting'
        };

        this.plugins.set(pluginId, plugin);
        plugin.status = 'running';

        res.json({
          pluginId,
          name,
          port,
          status: 'deployed'
        });
      } catch (error) {
        res.status(500).json({ error: String(error) });
      }
    });

    this.app.get('/plugins/:id', (req: Request, res: Response) => {
      const plugin = this.plugins.get(req.params.id);
      if (!plugin) {
        return res.status(404).json({ error: 'Plugin not found' });
      }
      res.json(plugin);
    });

    this.app.delete('/plugins/:id', (req: Request, res: Response) => {
      const plugin = this.plugins.get(req.params.id);
      if (!plugin) {
        return res.status(404).json({ error: 'Plugin not found' });
      }

      if (plugin.process) {
        plugin.process.kill();
      }

      if (plugin.healthCheck) {
        clearInterval(plugin.healthCheck);
      }

      this.plugins.delete(req.params.id);
      res.json({ status: 'deleted' });
    });

    this.app.get('/plugins/:id/health', async (req: Request, res: Response) => {
      const plugin = this.plugins.get(req.params.id);
      if (!plugin) {
        return res.status(404).json({ error: 'Plugin not found' });
      }

      if (plugin.status === 'running') {
        res.json({ status: 'healthy', pluginId: plugin.id });
      } else {
        res.status(503).json({ status: 'unhealthy', pluginId: plugin.id });
      }
    });
  }

  start(port: number = 3001) {
    this.basePort = port;
    this.app.listen(port, () => {
      console.log(`Plugin Runtime started on port ${port}`);
    });
  }
}

export default PluginRuntime;
