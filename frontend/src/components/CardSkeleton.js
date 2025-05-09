/**
 * Card Skeleton Component for BU MET Autograder
 * Provides placeholder loading states for better UX
 */

import React from 'react';
import { Box, Card, CardContent, Skeleton } from '@mui/material';
import { styled } from '@mui/material/styles';
import PropTypes from 'prop-types';

// Styled components
const StyledCard = styled(Card)(({ theme }) => ({
  height: '100%',
  display: 'flex',
  flexDirection: 'column',
}));

const SkeletonContainer = styled(CardContent)(({ theme }) => ({
  display: 'flex',
  flexDirection: 'column',
  flexGrow: 1,
}));

// CardSkeleton component
const CardSkeleton = ({
  height = 200,
  animation = 'pulse',
  variant = 'rectangular',
  count = 1,
}) => {
  // Generate multiple skeletons if count > 1
  if (count > 1) {
    return (
      <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 2 }}>
        {Array.from(new Array(count)).map((_, index) => (
          <CardSkeleton
            key={index}
            height={height}
            animation={animation}
            variant={variant}
            count={1}
          />
        ))}
      </Box>
    );
  }

  return (
    <StyledCard>
      <SkeletonContainer>
        <Skeleton
          variant="text"
          animation={animation}
          height={28}
          width="60%"
          sx={{ mb: 1 }}
        />
        <Skeleton
          variant="text"
          animation={animation}
          height={20}
          width="40%"
          sx={{ mb: 2 }}
        />
        <Skeleton
          variant={variant}
          animation={animation}
          height={height - 100 > 0 ? height - 100 : 20}
          sx={{ mb: 1, flexGrow: 1 }}
        />
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 'auto' }}>
          <Skeleton
            variant="text"
            animation={animation}
            height={20}
            width="30%"
          />
          <Skeleton
            variant="rounded"
            animation={animation}
            height={36}
            width="20%"
          />
        </Box>
      </SkeletonContainer>
    </StyledCard>
  );
};

// PropTypes for type checking
CardSkeleton.propTypes = {
  height: PropTypes.number,
  animation: PropTypes.oneOf(['pulse', 'wave', false]),
  variant: PropTypes.oneOf(['text', 'rectangular', 'rounded', 'circular']),
  count: PropTypes.number,
};

export default CardSkeleton;