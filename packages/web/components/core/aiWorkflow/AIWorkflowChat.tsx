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
  AlertIcon
} from '@chakra-ui/react';
import { sendMessage, confirmWorkflow } from './api';

interface Question {
  id: string;
  question: string;
  options?: string[];
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  workflowPreview?: {
    nodes: any[];
    edges: any[];
  };
  status?: 'ready' | 'need_more_info' | 'failed' | 'generating';
  questions?: Question[];
  nextQuestion?: string;
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
  const toast = useToast();

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
      setIsLoading(true);

      try {
        const response = await sendMessage({
          teamId,
          message: textToSend,
          sessionId: currentSessionId
        });

        const newSessionId = response.sessionId || currentSessionId;
        setCurrentSessionId(newSessionId);

        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: response.message,
          workflowPreview: response.workflowPreview,
          status: response.status,
          questions: response.questions
        };

        setMessages((prev) => [...prev, assistantMessage]);

        if (response.questions && response.questions.length > 0) {
          setPendingQuestions(response.questions);
        }

        if (response.workflowPreview && response.status === 'ready' && onWorkflowCreated) {
          onWorkflowCreated(newSessionId);
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
    [input, isLoading, teamId, currentSessionId, toast, onWorkflowCreated]
  );

  const handleConfirm = useCallback(
    async (confirmed: boolean, answer?: string) => {
      if (!currentSessionId || isLoading) return;

      setIsLoading(true);
      setPendingQuestions([]);

      try {
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
          status: response.status,
          questions: response.questions
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
    [currentSessionId, isLoading, toast, onWorkflowCreated]
  );

  const handleOptionClick = useCallback(
    (option: string) => {
      handleSend(option);
    },
    [handleSend]
  );

  return (
    <Flex direction="column" h="100%" maxW="800px" mx="auto" p={4}>
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
            {msg.status === 'failed' && (
              <Alert status="error" mt={2} borderRadius="md">
                <AlertIcon />
                Workflow generation failed. Please try again.
              </Alert>
            )}
          </Box>
        ))}
        {pendingQuestions.length > 0 && !isLoading && (
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
        {isLoading && (
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
          disabled={isLoading}
        />
        <Button
          onClick={() => handleSend()}
          colorScheme="blue"
          isLoading={isLoading}
          isDisabled={!input.trim()}
        >
          Send
        </Button>
      </Flex>
    </Flex>
  );
}
