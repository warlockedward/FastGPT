import { useState, useEffect, useCallback, useRef } from 'react';

export interface WorkflowNode {
  id: string;
  flowNodeType: string;
  position?: { x: number; y: number };
  data?: Record<string, any>;
  inputs?: any[];
  outputs?: any[];
}

export interface WorkflowEdge {
  id?: string;
  source: string;
  target: string;
  sourceHandle?: string;
  targetHandle?: string;
}

export interface Workflow {
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
}

export interface StreamEvent {
  type: string;
  data: {
    progress: number;
    message?: string;
    intent?: string;
    complexity?: string;
    currentNode?: string;
    nodeId?: string;
    node?: WorkflowNode;
    partialWorkflow?: Workflow;
    level?: string;
    workflow?: Workflow;
    validation_issues?: Array<{ message: string; severity: string }>;
    low_confidence_mappings?: Array<{
      source_node_id: string;
      source_variable: string;
      target_node_id: string;
      target_variable: string;
      confidence: number;
    }>;
    status?: string;
    completed?: boolean;
    error?: string;
    sessionId?: string;
  };
}

interface UseWorkflowStreamOptions {
  teamId: string;
  message: string;
  sessionId?: string;
  context?: {
    workflowId?: string;
    mode?: 'create' | 'optimize' | 'extend';
  };
  onSessionId?: (sessionId: string) => void;
  onIntentDetected?: (intent: string, complexity: string) => void;
  onNodeGenerating?: (nodeId: string, nodeType: string, progress: number) => void;
  onNodeGenerated?: (node: WorkflowNode, workflow: Workflow, progress: number) => void;
  onValidationProgress?: (progress: number, level: string) => void;
  onComplete?: (
    workflow: Workflow,
    status: string,
    validationIssues: any[],
    lowConfMappings: any[]
  ) => void;
  onError?: (error: string) => void;
}

interface UseWorkflowStreamReturn {
  workflow: Workflow;
  progress: number;
  status: 'idle' | 'streaming' | 'complete' | 'error';
  currentNode: string;
  statusMessage: string;
  validationIssues: any[];
  lowConfidenceMappings: any[];
  startStream: () => Promise<void>;
  reset: () => void;
}

export function useWorkflowStream({
  teamId,
  message,
  sessionId,
  context,
  onSessionId,
  onIntentDetected,
  onNodeGenerating,
  onNodeGenerated,
  onValidationProgress,
  onComplete,
  onError
}: UseWorkflowStreamOptions): UseWorkflowStreamReturn {
  const [workflow, setWorkflow] = useState<Workflow>({ nodes: [], edges: [] });
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState<'idle' | 'streaming' | 'complete' | 'error'>('idle');
  const [currentNode, setCurrentNode] = useState('');
  const [statusMessage, setStatusMessage] = useState('');
  const [validationIssues, setValidationIssues] = useState<any[]>([]);
  const [lowConfidenceMappings, setLowConfidenceMappings] = useState<any[]>([]);
  const abortControllerRef = useRef<AbortController | null>(null);

  const parseEvent = (rawEvent: string): StreamEvent | null => {
    const eventMatch = rawEvent.match(/^event: (.+)$/m);
    const dataMatch = rawEvent.match(/^data: (.+)$/m);

    if (!eventMatch || !dataMatch) return null;

    try {
      return {
        type: eventMatch[1],
        data: JSON.parse(dataMatch[1])
      };
    } catch {
      return null;
    }
  };

  const startStream = useCallback(async () => {
    setWorkflow({ nodes: [], edges: [] });
    setProgress(0);
    setStatus('streaming');
    setCurrentNode('');
    setStatusMessage('');
    setValidationIssues([]);
    setLowConfidenceMappings([]);

    abortControllerRef.current = new AbortController();

    try {
      const response = await fetch('/api/core/workflow/ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          teamId,
          message,
          sessionId,
          stream: true,
          context
        }),
        signal: abortControllerRef.current.signal
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      if (!response.body) {
        throw new Error('No response body');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const event = parseEvent(line);
          if (!event) continue;

          const { type, data } = event;

          switch (type) {
            case 'aiWorkflowSession':
              if (data.sessionId) {
                onSessionId?.(data.sessionId);
              }
              break;

            case 'aiWorkflowIntent':
              setProgress(data.progress);
              setStatusMessage(data.message || '');
              if (data.intent && data.complexity) {
                onIntentDetected?.(data.intent, data.complexity);
              }
              break;

            case 'aiWorkflowNodeGenerating':
              setProgress(data.progress);
              setCurrentNode(data.currentNode || '');
              onNodeGenerating?.(data.nodeId || '', data.currentNode || '', data.progress);
              break;

            case 'aiWorkflowNodeGenerated':
              setCurrentNode('');
              setProgress(data.progress);
              if (data.partialWorkflow) {
                setWorkflow(data.partialWorkflow);
              }
              if (data.node) {
                onNodeGenerated?.(data.node, data.partialWorkflow || workflow, data.progress);
              }
              break;

            case 'aiWorkflowEdgeCreated':
              if (data.partialWorkflow) {
                setWorkflow(data.partialWorkflow);
              }
              break;

            case 'aiWorkflowValidationStart':
              setProgress(data.progress);
              break;

            case 'aiWorkflowValidationProgress':
              setProgress(data.progress);
              if (data.level) {
                onValidationProgress?.(data.progress, data.level);
              }
              break;

            case 'aiWorkflowMappingProgress':
              setProgress(data.progress);
              break;

            case 'aiWorkflowComplete':
              setProgress(100);
              setStatus('complete');
              setStatusMessage(data.message || '');

              if (data.workflow) {
                setWorkflow(data.workflow);
              }

              setValidationIssues(data.validation_issues || []);
              setLowConfidenceMappings(data.low_confidence_mappings || []);

              onComplete?.(
                data.workflow || workflow,
                data.status || 'ready',
                data.validation_issues || [],
                data.low_confidence_mappings || []
              );
              break;

            case 'error':
              setStatus('error');
              setStatusMessage(data.message || 'Unknown error');
              onError?.(data.message || 'Unknown error');
              break;
          }
        }
      }
    } catch (error) {
      if ((error as Error).name === 'AbortError') {
        setStatus('idle');
        return;
      }
      setStatus('error');
      setStatusMessage(String(error));
      onError?.(String(error));
    }
  }, [
    teamId,
    message,
    sessionId,
    context,
    onIntentDetected,
    onNodeGenerating,
    onNodeGenerated,
    onValidationProgress,
    onComplete,
    onError,
    workflow
  ]);

  const reset = useCallback(() => {
    abortControllerRef.current?.abort();
    setWorkflow({ nodes: [], edges: [] });
    setProgress(0);
    setStatus('idle');
    setCurrentNode('');
    setStatusMessage('');
    setValidationIssues([]);
    setLowConfidenceMappings([]);
  }, []);

  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  return {
    workflow,
    progress,
    status,
    currentNode,
    statusMessage,
    validationIssues,
    lowConfidenceMappings,
    startStream,
    reset
  };
}
