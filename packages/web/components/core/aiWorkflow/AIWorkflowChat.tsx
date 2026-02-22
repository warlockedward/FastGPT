'use client';

import { useState, useCallback } from 'react';
import {
  Box,
  Flex,
  Input,
  Button,
  VStack,
  Text,
  useToast
} from '@chakra-ui/react';
import { sendMessage } from './api';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  workflowPreview?: {
    nodes: any[];
    edges: any[];
  };
}

interface AIWorkflowChatProps {
  teamId: string;
  sessionId?: string;
  onWorkflowCreated?: (workflowId: string) => void;
}

export function AIWorkflowChat({
  teamId,
  sessionId,
  onWorkflowCreated
}: AIWorkflowChatProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const toast = useToast();

  const handleSend = useCallback(async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await sendMessage({
        teamId,
        message: input,
        sessionId
      });

      const assistantMessage: Message = {
        id: Date.now().toString(),
        role: 'assistant',
        content: response.message,
        workflowPreview: response.workflowPreview
      };

      setMessages((prev) => [...prev, assistantMessage]);

      if (response.workflowPreview && onWorkflowCreated) {
        onWorkflowCreated(response.sessionId);
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
  }, [input, isLoading, teamId, sessionId, toast, onWorkflowCreated]);

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
          </Box>
        ))}
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
          onClick={handleSend}
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
