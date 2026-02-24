"""
PluginCodeGenerator - Generates plugin code for FastGPT

This module provides:
1. Plugin code generation (TypeScript/JavaScript)
2. Plugin configuration (inputs/outputs schemas)
3. FastGPT plugin format conversion
4. Template-based code generation
"""
from __future__ import annotations
import re
import json
from enum import Enum
from typing import Optional, Dict, List, Any, Literal
from dataclasses import dataclass, field


class PluginLanguage(str, Enum):
    """Programming language for plugin"""
    TYPESCRIPT = "typescript"
    JAVASCRIPT = "javascript"
    PYTHON = "python"


@dataclass
class PluginInput:
    """Plugin input parameter"""
    name: str
    type: str  # string, number, boolean, object, array
    description: str = ""
    required: bool = True
    default: Any = None


@dataclass
class PluginOutput:
    """Plugin output parameter"""
    name: str
    type: str
    description: str = ""


@dataclass
class PluginSpec:
    """Specification for a plugin to be generated"""
    name: str
    description: str
    inputs: List[PluginInput]
    outputs: List[PluginOutput]
    implementation: str  # Core logic
    language: PluginLanguage = PluginLanguage.TYPESCRIPT
    version: str = "1.0.0"
    tags: List[str] = field(default_factory=list)


@dataclass
class GeneratedPluginCode:
    """Generated plugin code artifacts"""
    main_code: str
    config: Dict[str, Any]
    test_code: Optional[str] = None
    readme: Optional[str] = None


class PluginCodeGenerator:
    """
    Generates FastGPT-compatible plugin code.
    
    Supports:
    - TypeScript/JavaScript plugins
    - Custom inputs/outputs schemas
    - HTTP API integration
    - Tool definitions
    """
    
    # Input type mapping to TypeScript
    TS_TYPE_MAP = {
        "string": "string",
        "number": "number",
        "boolean": "boolean",
        "object": "Record<string, any>",
        "array": "string[]",
        "arrayString": "string[]",
        "arrayObject": "Record<string, any>[]",
    }
    
    def __init__(self):
        self.templates = self._load_templates()
    
    def _load_templates(self) -> Dict[str, str]:
        """Load code templates"""
        return {
            "typescript_http": self._ts_http_template(),
            "typescript_function": self._ts_function_template(),
            "typescript_tool": self._ts_tool_template(),
            "javascript_http": self._js_http_template(),
            "python_http": self._python_http_template(),
        }
    
    def generate(self, spec: PluginSpec) -> GeneratedPluginCode:
        """
        Generate plugin code from specification.
        
        Args:
            spec: Plugin specification
            
        Returns:
            GeneratedPluginCode with all artifacts
        """
        if spec.language == PluginLanguage.TYPESCRIPT:
            return self._generate_typescript(spec)
        elif spec.language == PluginLanguage.JAVASCRIPT:
            return self._generate_javascript(spec)
        elif spec.language == PluginLanguage.PYTHON:
            return self._generate_python(spec)
        else:
            raise ValueError(f"Unsupported language: {spec.language}")
    
    def _generate_typescript(self, spec: PluginSpec) -> GeneratedPluginCode:
        """Generate TypeScript plugin"""
        # Determine template based on implementation
        if "http" in spec.implementation.lower() or "request" in spec.implementation.lower():
            template = self.templates["typescript_http"]
            main_code = self._fill_ts_http_template(template, spec)
        elif "tool" in spec.tags:
            template = self.templates["typescript_tool"]
            main_code = self._fill_ts_tool_template(template, spec)
        else:
            template = self.templates["typescript_function"]
            main_code = self._fill_ts_function_template(template, spec)
        
        config = self._generate_config(spec)
        test_code = self._generate_test(spec)
        readme = self._generate_readme(spec)
        
        return GeneratedPluginCode(
            main_code=main_code,
            config=config,
            test_code=test_code,
            readme=readme
        )
    
    def _generate_javascript(self, spec: PluginSpec) -> GeneratedPluginCode:
        """Generate JavaScript plugin"""
        template = self.templates["javascript_http"]
        main_code = self._fill_js_template(template, spec)
        config = self._generate_config(spec)
        
        return GeneratedPluginCode(
            main_code=main_code,
            config=config
        )
    
    def _generate_python(self, spec: PluginSpec) -> GeneratedPluginCode:
        """Generate Python plugin"""
        template = self.templates["python_http"]
        main_code = self._fill_python_template(template, spec)
        config = self._generate_config(spec)
        
        return GeneratedPluginCode(
            main_code=main_code,
            config=config
        )
    
    def _generate_config(self, spec: PluginSpec) -> Dict[str, Any]:
        """Generate FastGPT plugin configuration"""
        return {
            "name": spec.name,
            "description": spec.description,
            "version": spec.version,
            "inputs": [
                {
                    "key": inp.name,
                    "label": self._camel_to_title(inp.name),
                    "type": "input",
                    "required": inp.required,
                    "description": inp.description,
                    "valueType": inp.type
                }
                for inp in spec.inputs
            ],
            "outputs": [
                {
                    "key": out.name,
                    "label": self._camel_to_title(out.name),
                    "type": "source",
                    "valueType": out.type,
                    "description": out.description
                }
                for out in spec.outputs
            ],
            "tags": spec.tags
        }
    
    def _generate_test(self, spec: PluginSpec) -> str:
        """Generate test code"""
        return f'''import {{ {self._pascal_case(spec.name)} }} from './{spec.name}';

describe('{spec.name} Plugin', () => {{
  it('should execute successfully', async () => {{
    const result = await {self._pascal_case(spec.name)}({{
{',\\n'.join([f'      {inp.name}: "test"' for inp in spec.inputs])}
    }});
    expect(result).toBeDefined();
  }});
}});
'''
    
    def _generate_readme(self, spec: PluginSpec) -> str:
        """Generate README"""
        inputs_md = "\n".join([
            f"- `{inp.name}` ({inp.type}): {inp.description or 'No description'}"
            for inp in spec.inputs
        ])
        outputs_md = "\n".join([
            f"- `{out.name}` ({out.type}): {out.description or 'No description'}"
            for out in spec.outputs
        ])
        
        return f'''# {spec.name}

{spec.description}

## Inputs

{inputs_md or "None"}

## Outputs

{outputs_md or "None"}

## Usage

```typescript
import {{ {self._pascal_case(spec.name)} }} from './{spec.name}';

const result = await {self._pascal_case(spec.name)}({{
{',\\n'.join([f'  {inp.name}: "value"' for inp in spec.inputs])}
}});
```
'''
    
    # ==================== Template Methods ====================
    
    def _ts_http_template(self) -> str:
        return '''import { PluginBase } from '@fastgpt/service/core/plugin/base';
import type { NextAPIHandler } from '@/pages/api/team/plugin/[id]';

/**
 * {{name}} Plugin
 * {{description}}
 */
class {{pascalName}} extends PluginBase {
  async execute(inputs: {{inputType}}): Promise<{{outputType}}> {
    const { {{inputFields}} } = inputs;
    
    try {
      // {{implementation}}
      {{execCode}}
      
      return {
        {{returnFields}}
      };
    } catch (error) {
      throw new Error(`{{name}} failed: ${error.message}`);
    }
  }
}

export default {{pascalName}};
'''
    
    def _ts_function_template(self) -> str:
        return '''import { PluginBase } from '@fastgpt/service/core/plugin/base';

/**
 * {{name}} Plugin
 * {{description}}
 */
class {{pascalName}} extends PluginBase {
  async execute(inputs: {{inputType}}): Promise<{{outputType}}> {
    const { {{inputFields}} } = inputs;
    
    // {{implementation}}
    {{execCode}}
    
    return {
      {{returnFields}}
    };
  }
}

export default {{pascalName}};
'''
    
    def _ts_tool_template(self) -> str:
        return '''import { Tool } from '@/types/core/workflow';

/**
 * {{name}} Tool
 * {{description}}
 */
export const {{camelName}}Tool: Tool = {
  name: '{{name}}',
  description: '{{description}}',
  parameters: {
    type: 'object',
    properties: {
      {{paramProperties}}
    },
    required: [{{requiredParams}}]
  },
  
  async execute(params: Record<string, any>): Promise<any> {
    const { {{inputFields}} } = params;
    
    // {{implementation}}
    {{execCode}}
    
    return {
      {{returnFields}}
    };
  }
};
'''
    
    def _js_http_template(self) -> str:
        return '''/**
 * {{name}} Plugin
 * {{description}}
 */
module.exports = {
  name: '{{name}}',
  version: '{{version}}',
  
  inputs: [{{inputDefs}}],
  outputs: [{{outputDefs}}],
  
  async execute(inputs, context) {
    const { {{inputFields}} } = inputs;
    
    // {{implementation}}
    {{execCode}}
    
    return {
      {{returnFields}}
    };
  }
};
'''
    
    def _python_http_template(self) -> str:
        return '''"""
{{name}} Plugin
{{description}}
"""
from typing import Dict, Any, List

class {{pascalName}}Plugin:
    """FastGPT Plugin"""
    
    name = "{{name}}"
    version = "{{version}}"
    
    @staticmethod
    def get_inputs() -> List[Dict[str, Any]]:
        return [{{inputDefs}}]
    
    @staticmethod
    def get_outputs() -> List[Dict[str, Any]]:
        return [{{outputDefs}}]
    
    @classmethod
    def execute(cls, inputs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        {{inputFields}} = inputs
        
        # {{implementation}}
        {{execCode}}
        
        return {
            {{returnFields}}
        }
'''
    
    # ==================== Template Fillers ====================
    
    def _fill_ts_http_template(self, template: str, spec: PluginSpec) -> str:
        return template \
            .replace("{{name}}", spec.name) \
            .replace("{{description}}", spec.description) \
            .replace("{{pascalName}}", self._pascal_case(spec.name)) \
            .replace("{{camelName}}", self._camel_case(spec.name)) \
            .replace("{{inputType}}", self._generate_input_ts_type(spec.inputs)) \
            .replace("{{outputType}}", self._generate_output_ts_type(spec.outputs)) \
            .replace("{{inputFields}}", ", ".join([i.name for i in spec.inputs])) \
            .replace("{{returnFields}}", ", ".join([f"{o.name}: result.{o.name}" for o in spec.outputs])) \
            .replace("{{implementation}}", spec.implementation) \
            .replace("{{execCode}}", self._generate_exec_code(spec))
    
    def _fill_ts_function_template(self, template: str, spec: PluginSpec) -> str:
        return self._fill_ts_http_template(template, spec)
    
    def _fill_ts_tool_template(self, template: str, spec: PluginSpec) -> str:
        props = []
        for inp in spec.inputs:
            props.append(f'      {inp.name}: {{ type: "{self._ts_type_map.get(inp.type, "string")}", description: "{inp.description}" }}')
        
        return template \
            .replace("{{name}}", spec.name) \
            .replace("{{description}}", spec.description) \
            .replace("{{pascalName}}", self._pascal_case(spec.name)) \
            .replace("{{camelName}}", self._camel_case(spec.name)) \
            .replace("{{paramProperties}}", ",\n".join(props)) \
            .replace("{{requiredParams}}", ", ".join([f'"{i.name}"' for i in spec.inputs if i.required])) \
            .replace("{{inputFields}}", ", ".join([i.name for i in spec.inputs])) \
            .replace("{{returnFields}}", ", ".join([f"{o.name}: result.{o.name}" for o in spec.outputs])) \
            .replace("{{implementation}}", spec.implementation) \
            .replace("{{execCode}}", self._generate_exec_code(spec))
    
    def _fill_js_template(self, template: str, spec: PluginSpec) -> str:
        input_defs = ", ".join([f'{{ key: "{i.name}", label: "{i.name}", type: "{i.type}" }}' for i in spec.inputs])
        output_defs = ", ".join([f'{{ key: "{o.name}", type: "{o.type}" }}' for o in spec.outputs])
        
        return template \
            .replace("{{name}}", spec.name) \
            .replace("{{description}}", spec.description) \
            .replace("{{version}}", spec.version) \
            .replace("{{inputDefs}}", input_defs) \
            .replace("{{outputDefs}}", output_defs) \
            .replace("{{inputFields}}", ", ".join([i.name for i in spec.inputs])) \
            .replace("{{returnFields}}", ", ".join([f"{o.name}: result.{o.name}" for o in spec.outputs])) \
            .replace("{{implementation}}", spec.implementation) \
            .replace("{{execCode}}", self._generate_exec_code(spec))
    
    def _fill_python_template(self, template: str, spec: PluginSpec) -> str:
        input_defs = ", ".join([f'{{"key": "{i.name}", "label": "{i.name}", "type": "{i.type}"}}' for i in spec.inputs])
        output_defs = ", ".join([f'{{"key": "{o.name}", "type": "{o.type}"}}' for o in spec.outputs])
        
        return template \
            .replace("{{name}}", spec.name) \
            .replace("{{description}}", spec.description) \
            .replace("{{version}}", spec.version) \
            .replace("{{pascalName}}", self._pascal_case(spec.name)) \
            .replace("{{inputDefs}}", input_defs) \
            .replace("{{outputDefs}}", output_defs) \
            .replace("{{inputFields}}", ", ".join([i.name for i in spec.inputs])) \
            .replace("{{returnFields}}", ", ".join([f'"{o.name}": result["{o.name}"]' for o in spec.outputs])) \
            .replace("{{implementation}}", spec.implementation) \
            .replace("{{execCode}}", self._generate_exec_code(spec))
    
    def _generate_exec_code(self, spec: PluginSpec) -> str:
        """Generate execution code based on implementation"""
        impl = spec.implementation.lower()
        
        if "http" in impl or "request" in impl or "api" in impl:
            return '''// Make HTTP request
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ {{inputFields}} })
      });
      const result = await response.json();'''
        
        if "transform" in impl:
            return '''// Transform data
      const result = { {{inputFields}} };'''
        
        if "calculate" in impl or "compute" in impl:
            return '''// Perform calculation
      const result = { {{inputFields}} };'''
        
        # Default implementation
        return '''// Process inputs
      const result = {
        {{returnFields}}
      };'''
    
    # ==================== Utility Methods ====================
    
    def _pascal_case(self, s: str) -> str:
        """Convert to PascalCase"""
        return re.sub(r'(?:^|[_-])([a-z])', lambda m: m.group(1).upper(), s)
    
    def _camel_case(self, s: str) -> str:
        """Convert to camelCase"""
        s = self._pascal_case(s)
        return s[0].lower() + s[1:] if s else s
    
    def _camel_to_title(self, s: str) -> str:
        """Convert camelCase to Title Case"""
        return re.sub(r'([A-Z])', r' \1', s).strip()
    
    @property
    def _ts_type_map(self) -> Dict[str, str]:
        return self.TS_TYPE_MAP
    
    def _generate_input_ts_type(self, inputs: List[PluginInput]) -> str:
        """Generate TypeScript input type"""
        if not inputs:
            return "Record<string, any>"
        
        props = []
        for inp in inputs:
            ts_type = self.TS_TYPE_MAP.get(inp.type, "string")
            optional = "" if inp.required else "?"
            props.append(f"  {inp.name}{optional}: {ts_type}")
        
        return f"{{\n{',\\n'.join(props)}\n}}"
    
    def _generate_output_ts_type(self, outputs: List[PluginOutput]) -> str:
        """Generate TypeScript output type"""
        if not outputs:
            return "Record<string, any>"
        
        props = []
        for out in outputs:
            ts_type = self.TS_TYPE_MAP.get(out.type, "string")
            props.append(f"  {out.name}: {ts_type}")
        
        return f"{{\n{',\\n'.join(props)}\n}}"


# Factory function
def create_plugin_generator(language: PluginLanguage = PluginLanguage.TYPESCRIPT) -> PluginCodeGenerator:
    """Create a plugin code generator"""
    return PluginCodeGenerator()
