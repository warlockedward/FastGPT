'use client';

import { Box, Flex, Text, VStack, HStack, Badge } from '@chakra-ui/react';

interface NodeData {
  id: string;
  flowNodeType: string;
  name?: string;
  intro?: string;
  data?: {
    name?: string;
    label?: string;
    intro?: string;
  };
}

interface EdgeData {
  source: string;
  target: string;
}

interface WorkflowPreviewProps {
  nodes: NodeData[];
  edges: EdgeData[];
  onNodeClick?: (nodeId: string) => void;
}

export function WorkflowPreview({ nodes, edges, onNodeClick }: WorkflowPreviewProps) {
  return (
    <Box p={4} bg="gray.50" borderRadius="lg" minH="300px" position="relative" overflow="auto">
      <Text fontWeight="bold" mb={4}>
        Workflow Preview
      </Text>

      {nodes.length === 0 ? (
        <Flex h="200px" align="center" justify="center" color="gray.400">
          <Text>No workflow generated yet</Text>
        </Flex>
      ) : (
        <VStack spacing={4} align="stretch">
          <Box>
            <Text fontSize="sm" fontWeight="medium" mb={2}>
              Nodes ({nodes.length})
            </Text>
            <HStack flexWrap="wrap" gap={2}>
              {nodes.map((node) => (
                <Badge
                  key={node.id}
                  colorScheme="blue"
                  cursor="pointer"
                  onClick={() => onNodeClick?.(node.id)}
                  px={2}
                  py={1}
                  borderRadius="md"
                >
                  {node.name || node.data?.name || node.data?.label || node.flowNodeType}
                </Badge>
              ))}
            </HStack>
          </Box>

          <Box>
            <Text fontSize="sm" fontWeight="medium" mb={2}>
              Connections ({edges.length})
            </Text>
            <VStack align="stretch" spacing={1}>
              {edges.map((edge, idx) => (
                <Text key={idx} fontSize="sm" color="gray.600">
                  {edge.source} → {edge.target}
                </Text>
              ))}
            </VStack>
          </Box>
        </VStack>
      )}
    </Box>
  );
}
