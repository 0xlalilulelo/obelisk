import type { AthleteProfileInput, CreateBlockInput } from '@obelisk/types';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { useApi } from './api';

export const queryKeys = {
  profile: ['profile'] as const,
  blocks: ['blocks'] as const,
  block: (id: string) => ['block', id] as const,
  plan: (id: string) => ['plan', id] as const,
  messages: (id: string) => ['messages', id] as const,
};

export function useProfile() {
  const api = useApi();
  return useQuery({
    queryKey: queryKeys.profile,
    queryFn: () => api.getProfile().catch(() => null),
  });
}

export function useUpsertProfile() {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: AthleteProfileInput) => api.upsertProfile(body),
    onSuccess: (profile) => qc.setQueryData(queryKeys.profile, profile),
  });
}

export function useBlocks() {
  const api = useApi();
  return useQuery({ queryKey: queryKeys.blocks, queryFn: () => api.listBlocks() });
}

export function useBlock(id: string | null) {
  const api = useApi();
  return useQuery({
    queryKey: id ? queryKeys.block(id) : ['block', 'none'],
    queryFn: () => api.getBlock(id as string),
    enabled: !!id,
  });
}

export function useMessages(id: string | null) {
  const api = useApi();
  return useQuery({
    queryKey: id ? queryKeys.messages(id) : ['messages', 'none'],
    queryFn: () => api.getMessages(id as string),
    enabled: !!id,
  });
}

export function useCreateBlock() {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateBlockInput) => api.createBlock(body),
    onSuccess: (block) => {
      qc.invalidateQueries({ queryKey: queryKeys.blocks });
      qc.setQueryData(queryKeys.block(block.id), block);
    },
  });
}

export function useCommitEdit(blockId: string) {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (editId: string) => api.commitEdit(blockId, editId),
    onSuccess: (block) => {
      qc.setQueryData(queryKeys.block(blockId), block);
      qc.invalidateQueries({ queryKey: queryKeys.plan(blockId) });
    },
  });
}

export function useRejectEdit(blockId: string) {
  const api = useApi();
  return useMutation({
    mutationFn: (editId: string) => api.rejectEdit(blockId, editId),
  });
}
