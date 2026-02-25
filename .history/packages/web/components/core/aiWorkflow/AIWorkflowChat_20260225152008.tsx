'use client';

import { useState, useCallback } from 'react';
import {
  Box,
  Flex,
  Input,
  Button,
  VStack,
  Text,
  useToast,
  HStack,
  Badge,
  Alert,
  AlertIcon,
  Accordion,
  AccordionItem,
  AccordionButton,
  AccordionPanel,
  AccordionIcon,
  Progress,
  Spinner
} from '@chakra-ui/react';
import { sendMessage, confirmWorkflow, confirmMappings } from './api';
import { useWorkflowStream } from './useWorkflowStream';
import { WorkflowPreview } from './WorkflowPreview';

interface Question {
  id: string;
  question: string;
  options?: string[];
}

interface ValidationIssue {
  message: string;
  severity: string;
  level?: string;
}

interface LowConfidenceMapping {
  source_node_id: string;
  source_variable: string;
  target_node_id: string;
  target_variable: string;
  confidence: number;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  workflowPreview?: {
    nodes: any[];
    edges: any[];
  };
  status?: 'ready' | 'need_more_info' | 'failed' | 'generating' | 'reviewing';
  questions?: Question[];
  validation_issues?: ValidationIssue[];
  low_confidence_mappings?: LowConfidenceMapping[];
}

interface AIWorkflowChatProps {
  teamId: string;
  sessionId?: string;
  onWorkflowCreated?: (workflowId: string) => void;
}

export function AIWorkflowChat({ teamId, sessionId, onWorkflowCreated }: AIWorkflowChatProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [currentSessionId, setCurrentSessionId] = useState(sessionId);
  const [pendingQuestions, setPendingQuestions] = useState<Question[]>([]);
  const [validationIssues, setValidationIssues] = useState<ValidationIssue[]>([]);
  const [lowConfidenceMappings, setLowConfidenceMappings] = useState<LowConfidenceMapping[]>([]);
  const [useStreaming, setUseStreaming] = useState(true);
  const toast = useToast();

  // Streaming hook
  const {
    workflow: streamingWorkflow,
    progress,
    status: streamStatus,
    currentNode,
    statusMessage,
    validationIssues: streamValidationIssues,
    lowConfidenceMappings: streamLowConfidenceMappings,
    startStream
  } = useWorkflowStream({
    teamId,
    message: input,
    sessionId: currentSessionId,
    onSessionId: (id) => {
      setCurrentSessionId(id);
    },
    onComplete: (workflow, status, issues, mappings) => {
      setValidationIssues(issues);
      setLowConfidenceMappings(mappings);

      const assistantMessage: Message = {
        id: Date.now().toString(),
        role: 'assistant',
        content: '工作流已生成',
        workflowPreview: workflow,
        status: status as any,
        validation_issues: issues,
        low_confidence_mappings: mappings
      };
      setMessages((prev) => [...prev, assistantMessage]);

      if (status === 'ready' && onWorkflowCreated) {
        onWorkflowCreated(currentSessionId || '');
      }
    },
    onError: (error) => {
      toast({ title: 'Error', description: error, status: 'error', duration: 5000 });
    }
  });

  const handleSend = useCallback(
    async (messageText?: string) => {
      const textToSend = messageText || input;
      if (!textToSend.trim() || isLoading) return;

      const userMessage: Message = {
        id: Date.now().toString(),
        role: 'user',
        content: textToSend
      };

      setMessages((prev) => [...prev, userMessage]);
      if (!messageText) {
        setInput('');
      }

      // Use streaming mode
      if (useStreaming) {
        try {
          await startStream();
        } catch (error) {
          toast({
            title: 'Error',
            description: 'Failed to start streaming',
            status: 'error',
            duration: 3000
          });
        }
        return;
      }

      // Non-streaming mode (fallback)
      setIsLoading(true);
      try {
        const response = await sendMessage({
          teamId,
          message: textToSend,
          sessionId: currentSessionId
        });

        const newSessionId = response.sessionId || currentSessionId;
        setCurrentSessionId(newSessionId);

        setValidationIssues(response.validation_issues || []);
        setLowConfidenceMappings(response.low_confidence_mappings || []);

        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: response.message,
          workflowPreview: response.workflowPreview,
          status: response.status,
          questions: response.questions,
          validation_issues: response.validation_issues,
          low_confidence_mappings: response.low_confidence_mappings
        };

        setMessages((prev) => [...prev, assistantMessage]);

        if (response.questions && response.questions.length > 0) {
          setPendingQuestions(response.questions);
        }

        if (response.workflowPreview && response.status === 'ready' && onWorkflowCreated) {
          onWorkflowCreated(newSessionId);
        }

        if (
          response.status === 'reviewing' &&
          response.low_confidence_mappings &&
          response.low_confidence_mappings.length > 0
        ) {
          toast({
            title: 'Review Required',
            description: `${response.low_confidence_mappings.length} variable mappings need your confirmation`,
            status: 'warning',
            duration: 5000
          });
        }
      } catch (error) {
        toast({
          title: 'Error',
          description: 'Failed to send message',
          status: 'error',
          duration: 3000
        });
      } finally {
        setIsLoading(false);
      }
    },
    [
      input,
      isLoading,
      teamId,
      currentSessionId,
      toast,
      onWorkflowCreated,
      useStreaming,
      startStream
    ]
  );

  const handleConfirm = useCallback(
    async (confirmed: boolean, answer?: string) => {
      if (!currentSessionId || isLoading) return;

      setIsLoading(true);
      setPendingQuestions([]);
      setValidationIssues([]);
      setLowConfidenceMappings([]);

      try {
        if (confirmed && lowConfidenceMappings.length > 0 && currentSessionId) {
          await confirmMappings(
            currentSessionId,
            lowConfidenceMappings.map((m) => ({
              source_node_id: m.source_node_id,
              target_node_id: m.target_node_id
            }))
          );
        }

        const response = await confirmWorkflow({
          sessionId: currentSessionId,
          answer: answer || '',
          confirmed
        });

        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: response.message || response.nextQuestion || '',
          workflowPreview: response.workflow || response.workflowPreview,
          status: response.status
        };

        setMessages((prev) => [...prev, assistantMessage]);

        if (response.workflow && onWorkflowCreated) {
          onWorkflowCreated(response.sessionId);
        }
      } catch (error) {
        toast({
          title: 'Error',
          description: 'Failed to confirm',
          status: 'error',
          duration: 3000
        });
      } finally {
        setIsLoading(false);
      }
    },
    [currentSessionId, isLoading, lowConfidenceMappings, toast, onWorkflowCreated]
  );

  const handleOptionClick = useCallback(
    (option: string) => {
      handleSend(option);
    },
    [handleSend]
  );

  const isStreaming = streamStatus === 'streaming';

  return (
    <Flex direction="column" h="100%" maxW="800px" mx="auto" p={4}>
      {/* Streaming Progress UI */}
      {isStreaming && (
        <Box mb={4} p={4} bg="blue.50" borderRadius="lg">
          <HStack justify="space-between" mb={2}>
            <HStack>
              <Spinner size="sm" />
              <Text fontWeight="bold">Generating Workflow...</Text>
            </HStack>
            <Badge colorScheme="blue">{progress}%</Badge>
          </HStack>
          <Progress value={progress} colorScheme="blue" borderRadius="full" mb={2} />
          <Text fontSize="sm" color="gray.600">
            {currentNode ? `Generating node: ${currentNode}` : statusMessage || 'Processing...'}
          </Text>
          {streamingWorkflow.nodes.length > 0 && (
            <Text fontSize="sm" color="gray.500" mt={1}>
              {streamingWorkflow.nodes.length} nodes, {streamingWorkflow.edges.length} edges
            </Text>
          )}
        </Box>
      )}

      <VStack flex={1} overflowY="auto" spacing={4} align="stretch" mb={4}>
        {messages.map((msg) => (
          <Box
            key={msg.id}
            p={4}
            borderRadius="lg"
            bg={msg.role === 'user' ? 'blue.50' : 'gray.50'}
            alignSelf={msg.role === 'user' ? 'flex-end' : 'flex-start'}
            maxW="80%"
          >
            <Text whiteSpace="pre-wrap">{msg.content}</Text>
            {msg.workflowPreview && (
              <Box mt={2} p={2} bg="white" borderRadius="md" fontSize="sm">
                <Text fontWeight="bold">Workflow Preview:</Text>
                <Text>
                  {msg.workflowPreview.nodes?.length || 0} nodes,{' '}
                  {msg.workflowPreview.edges?.length || 0} edges
                </Text>
              </Box>
            )}
            {msg.status === 'reviewing' && (
              <Alert status="warning" mt={2} borderRadius="md">
                <AlertIcon />
                Please review the variable mappings and validation issues below.
              </Alert>
            )}
            {msg.status === 'failed' && (
              <Alert status="error" mt={2} borderRadius="md">
                <AlertIcon />
                Workflow generation failed. Please try again.
              </Alert>
            )}
          </Box>
        ))}

        {(validationIssues.length > 0 || lowConfidenceMappings.length > 0) && !isStreaming && (
          <Accordion allowMultiple>
            <AccordionItem>
              <AccordionButton>
                <Box flex="1" textAlign="left">
                  <Text fontWeight="bold">Validation Issues ({validationIssues.length})</Text>
                </Box>
                <AccordionIcon />
              </AccordionButton>
              <AccordionPanel pb={4}>
                {validationIssues.map((issue, idx) => (
                  <Alert
                    key={idx}
                    status={issue.severity === 'error' ? 'error' : 'warning'}
                    mb={2}
                    borderRadius="md"
                  >
                    <AlertIcon />
                    <Text fontSize="sm">{issue.message}</Text>
                  </Alert>
                ))}
              </AccordionPanel>
            </AccordionItem>

            <AccordionItem>
              <AccordionButton>
                <Box flex="1" textAlign="left">
                  <Text fontWeight="bold">Variable Mappings ({lowConfidenceMappings.length})</Text>
                </Box>
                <AccordionIcon />
              </AccordionButton>
              <AccordionPanel pb={4}>
                {lowConfidenceMappings.map((mapping, idx) => (
                  <Box key={idx} p={2} bg="orange.50" mb={2} borderRadius="md">
                    <HStack justify="space-between">
                      <Text fontSize="sm">
                        {mapping.source_variable} → {mapping.target_variable}
                      </Text>
                      <Badge colorScheme="orange">{Math.round(mapping.confidence * 100)}%</Badge>
                    </HStack>
                  </Box>
                ))}
                <HStack mt={3}>
                  <Button size="sm" colorScheme="green" onClick={() => handleConfirm(true)}>
                    Confirm All
                  </Button>
                  <Button
                    size="sm"
                    colorScheme="red"
                    variant="outline"
                    onClick={() => handleConfirm(false)}
                  >
                    Cancel
                  </Button>
                </HStack>
              </AccordionPanel>
            </AccordionItem>
          </Accordion>
        )}

        {pendingQuestions.length > 0 && !isStreaming && (
          <Box p={4} borderRadius="lg" bg="orange.50" alignSelf="flex-start" maxW="80%">
            <Text fontWeight="bold" mb={2}>
              Please answer:
            </Text>
            <VStack align="stretch" spacing={2}>
              {pendingQuestions.map((q) => (
                <Box key={q.id}>
                  <Text mb={2}>{q.question}</Text>
                  {q.options ? (
                    <HStack flexWrap="wrap" gap={2}>
                      {q.options.map((opt, idx) => (
                        <Button
                          key={idx}
                          size="sm"
                          colorScheme="blue"
                          variant="outline"
                          onClick={() => handleOptionClick(opt)}
                        >
                          {opt}
                        </Button>
                      ))}
                    </HStack>
                  ) : (
                    <Input
                      placeholder="Your answer..."
                      onKeyPress={(e) => {
                        if (e.key === 'Enter') {
                          handleOptionClick((e.target as HTMLInputElement).value);
                        }
                      }}
                    />
                  )}
                </Box>
              ))}
            </VStack>
            <HStack mt={3}>
              <Button size="sm" colorScheme="green" onClick={() => handleConfirm(true)}>
                Confirm
              </Button>
              <Button
                size="sm"
                colorScheme="red"
                variant="outline"
                onClick={() => handleConfirm(false)}
              >
                Cancel
              </Button>
            </HStack>
          </Box>
        )}
        {isLoading && !isStreaming && (
          <Box p={4} borderRadius="lg" bg="gray.50" alignSelf="flex-start">
            <Text color="gray.500">Thinking...</Text>
          </Box>
        )}
      </VStack>

      <Flex gap={2}>
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Describe the workflow you want to create..."
          onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
          disabled={isLoading || isStreaming}
        />
        <Button
          onClick={() => handleSend()}
          colorScheme="blue"
          isLoading={isLoading || isStreaming}
          isDisabled={!input.trim()}
        >
          {isStreaming ? 'Generating...' : 'Send'}
        </Button>
      </Flex>
    </Flex>
  );
}
