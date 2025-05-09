import React from 'react';
import { useRouter } from 'next/router';

export default function TestPage() {
  const router = useRouter();
  const { id, semester } = router.query;
  return (
    <div>
      <h1>Test Page</h1>
      <p>Course ID: {id}</p>
      <p>Semester: {semester}</p>
    </div>
  );
}