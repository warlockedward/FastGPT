'use client';

import { useState } from 'react';
import {
  Box,
  Flex,
  Text,
  VStack,
  HStack,
  Badge,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalCloseButton,
  ModalBody,
  ModalFooter,
  Button,
  useDisclosure,
  Code,
  useToast,
  Textarea
} from '@chakra-ui/react';
import { validateCode } from './api';

interface NodeData {
  id: string;
  flowNodeType: string;
  name?: string;
  intro?: string;
  data?: {
    name?: string;
    label?: string;
    intro?: string;
    code?: string;
  };
  inputs?: Array<{
    name: string;
    value?: any;
    label?: string;
    type?: string;
  }>;
  outputs?: Array<{
    name: string;
    label?: string;
    type?: string;
  }>;
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
  const [selectedNode, setSelectedNode] = useState<NodeData | null>(null);
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [validationResult, setValidationResult] = useState<string>('');
  const [isValidating, setIsValidating] = useState(false);
  const toast = useToast();

  const handleNodeClick = (node: NodeData) => {
    setSelectedNode(node);
    setValidationResult('');
    onOpen();
    onNodeClick?.(node.id);
  };

  const getNodeCode = (node: NodeData): { code: string; language: string } | undefined => {
    const code =
      node.data?.code ||
      node.inputs?.find((input) => input.name === 'code' || input.name === 'source')?.value;
    if (!code) return undefined;

    const language = node.inputs?.find((input) => input.name === 'language')?.value || 'javascript';
    return { code, language };
  };

  const handleValidate = async () => {
    if (!selectedNode) return;
    const nodeData = getNodeCode(selectedNode);
    if (!nodeData) return;

    setIsValidating(true);
    setValidationResult('');

    try {
      const result = await validateCode({
        code: nodeData.code,
        language: nodeData.language,
        inputs: {} // TODO: Allow user to provide test inputs
      });

      if (result.valid) {
        toast({
          title: 'Validation Passed',
          status: 'success',
          duration: 3000
        });
        setValidationResult(result.output || 'No output');
      } else {
        toast({
          title: 'Validation Failed',
          status: 'error',
          duration: 3000
        });
        setValidationResult(result.error || 'Unknown error');
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: String(error),
        status: 'error',
        duration: 3000
      });
      setValidationResult(String(error));
    } finally {
      setIsValidating(false);
    }
  };

  const selectedNodeCode = selectedNode ? getNodeCode(selectedNode)?.code : undefined;

  return (
    <>
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
                    onClick={() => handleNodeClick(node)}
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

      <Modal isOpen={isOpen} onClose={onClose} size="xl">
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>
            {selectedNode?.name || selectedNode?.data?.name || selectedNode?.flowNodeType}
          </ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <VStack align="stretch" spacing={4}>
              <Box>
                <Text fontWeight="bold" mb={2}>
                  ID
                </Text>
                <Text fontSize="sm" color="gray.600">
                  {selectedNode?.id}
                </Text>
              </Box>

              <Box>
                <Text fontWeight="bold" mb={2}>
                  Type
                </Text>
                <Badge>{selectedNode?.flowNodeType}</Badge>
              </Box>

              {selectedNodeCode && (
                <Box>
                  <Text fontWeight="bold" mb={2}>
                    Code
                  </Text>
                  <Box
                    p={4}
                    bg="gray.900"
                    color="green.300"
                    borderRadius="md"
                    maxH="300px"
                    overflow="auto"
                    fontSize="sm"
                    fontFamily="monospace"
                  >
                    <pre>{selectedNodeCode}</pre>
                  </Box>

                  {validationResult && (
                    <Box mt={4}>
                      <Text fontWeight="bold" mb={2}>
                        Result
                      </Text>
                      <Box
                        p={3}
                        bg="gray.100"
                        borderRadius="md"
                        maxH="150px"
                        overflow="auto"
                        fontSize="sm"
                        whiteSpace="pre-wrap"
                      >
                        {validationResult}
                      </Box>
                    </Box>
                  )}
                </Box>
              )}

              {selectedNode?.inputs && selectedNode.inputs.length > 0 && (
                <Box>
                  <Text fontWeight="bold" mb={2}>
                    Inputs
                  </Text>
                  <VStack align="stretch" spacing={2}>
                    {selectedNode.inputs.map((input, idx) => (
                      <Box key={idx} p={2} bg="gray.50" borderRadius="md">
                        <Text fontSize="xs" fontWeight="bold">
                          {input.name}
                        </Text>
                        <Text fontSize="sm" isTruncated>
                          {String(input.value)}
                        </Text>
                      </Box>
                    ))}
                  </VStack>
                </Box>
              )}
            </VStack>
          </ModalBody>
          <ModalFooter>
            {selectedNodeCode && (
              <Button colorScheme="blue" mr={3} onClick={handleValidate} isLoading={isValidating}>
                Validate Code
              </Button>
            )}
            <Button onClick={onClose}>Close</Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </>
  );
}
