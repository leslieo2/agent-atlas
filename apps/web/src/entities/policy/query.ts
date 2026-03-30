import { useQuery } from "@tanstack/react-query";
import { listPolicies } from "./api";

export const policiesQueryRoot = ["policies"] as const;

export function usePoliciesQuery() {
  return useQuery({
    queryKey: policiesQueryRoot,
    queryFn: listPolicies
  });
}
