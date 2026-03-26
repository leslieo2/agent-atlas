export interface AgentRecord {
  agentId: string;
  name: string;
  description: string;
  framework: string;
  entrypoint: string;
  defaultModel: string;
  tags: string[];
}
