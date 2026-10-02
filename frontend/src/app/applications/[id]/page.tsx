import { ApplicationDetailClient } from '@/components/applications/ApplicationDetailClient';
export default async function ApplicationPage({params}: {params: Promise<{id: string}>}) {
  const {id} = await params;
  return <ApplicationDetailClient applicationId={id} />;
}
