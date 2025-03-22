/**
 * AI Suggestion Card Component for BU MET Autograder
 * Displays AI-generated rubric suggestions
 */

import React, { useState } from 'react';
import {
  Box,
  Button,
  Card,
  CardActions,
  CardContent,
  Collapse,
  Divider,
  IconButton,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Paper,
  Tooltip,
  Typography,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import {
  Check as CheckIcon,
  Close as CloseIcon,
  ExpandMore as ExpandMoreIcon,
  Lightbulb as LightbulbIcon,
  RuleFolder as RubricIcon,
  Assignment as CriteriaIcon,
} from '@mui/icons-material';
import PropTypes from 'prop-types';

// Styled components
const SuggestionCard = styled(Card)(({ theme }) => ({
  position: 'relative',
  marginBottom: theme.spacing(3),
  backgroundColor: theme.palette.mode === 'dark'
    ? theme.palette.background.paper
    : theme.palette.common.white,
  boxShadow: theme.shadows[4],
  borderLeft: `4px solid ${theme.palette.warning.main}`,
}));

const ExpandButton = styled(IconButton)(({ theme, expanded }) => ({
  transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)',
  transition: theme.transitions.create('transform', {
    duration: theme.transitions.duration.shortest,
  }),
}));

const CriteriaItem = styled(ListItem)(({ theme }) => ({
  backgroundColor: theme.palette.background.default,
  borderRadius: theme.shape.borderRadius,
  marginBottom: theme.spacing(1),
}));

// AI Suggestion Card component
const AISuggestionCard = ({ rubric, onApply, onDismiss }) => {
  const [expanded, setExpanded] = useState(false);

  // Toggle expanded state
  const handleExpandClick = () => {
    setExpanded(!expanded);
  };

  // Handle applying the suggestion
  const handleApply = () => {
    if (onApply) onApply(rubric);
  };

  // Handle dismissing the suggestion
  const handleDismiss = () => {
    if (onDismiss) onDismiss();
  };

  return (
    <SuggestionCard>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
          <LightbulbIcon sx={{ color: 'warning.main', mr: 1 }} />
          <Typography variant="h6">
            AI-Generated Rubric Suggestion
          </Typography>
        </Box>

        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Our AI has analyzed your assignment and generated a suggested rubric. Review the suggestion and apply it if you find it useful.
        </Typography>

        <Paper
          elevation={0}
          sx={{ bgcolor: 'background.default', p: 2, borderRadius: 1 }}
        >
          <Typography variant="subtitle1" gutterBottom>
            <RubricIcon fontSize="small" sx={{ mr: 1, verticalAlign: 'middle' }} />
            Overall Guidelines
          </Typography>
          <Typography variant="body2" paragraph>
            {rubric.overall_instructor_guidelines || 'No overall guidelines provided.'}
          </Typography>
        </Paper>

        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 2 }}>
          <Typography variant="subtitle1">
            {rubric.sub_rubrics.length} Questions
          </Typography>

          <ExpandButton
            expanded={expanded}
            onClick={handleExpandClick}
            aria-expanded={expanded}
            aria-label="show more"
            size="small"
          >
            <ExpandMoreIcon />
          </ExpandButton>
        </Box>
      </CardContent>

      <Collapse in={expanded} timeout="auto" unmountOnExit>
        <CardContent sx={{ pt: 0 }}>
          <Divider sx={{ my: 2 }} />

          {rubric.sub_rubrics.map((subRubric, index) => (
            <Box key={`subRubric-${index}`} sx={{ mb: 3 }}>
              <Typography variant="subtitle1" gutterBottom>
                Question {subRubric.question_index + 1} - {subRubric.max_points} points
              </Typography>

              <Typography variant="body2" paragraph>
                {subRubric.instructor_guideline || 'No specific guidelines for this question.'}
              </Typography>

              {subRubric.grading_criteria && subRubric.grading_criteria.length > 0 && (
                <List dense disablePadding>
                  {subRubric.grading_criteria.map((criteria, criteriaIndex) => (
                    <CriteriaItem key={`criteria-${criteriaIndex}`}>
                      <ListItemIcon>
                        <CriteriaIcon fontSize="small" color="primary" />
                      </ListItemIcon>
                      <ListItemText
                        primary={criteria.criteria_id}
                        secondary={
                          <>
                            {criteria.criteria}
                            <Typography
                              component="span"
                              variant="body2"
                              color="primary"
                              sx={{ display: 'block', mt: 0.5 }}
                            >
                              {criteria.points} points
                            </Typography>
                          </>
                        }
                      />
                    </CriteriaItem>
                  ))}
                </List>
              )}
            </Box>
          ))}
        </CardContent>
      </Collapse>

      <Divider />

      <CardActions sx={{ justifyContent: 'flex-end' }}>
        <Tooltip title="Dismiss suggestion">
          <IconButton onClick={handleDismiss} size="small">
            <CloseIcon />
          </IconButton>
        </Tooltip>

        <Button
          variant="contained"
          color="primary"
          startIcon={<CheckIcon />}
          onClick={handleApply}
        >
          Apply Suggestion
        </Button>
      </CardActions>
    </SuggestionCard>
  );
};

// PropTypes for type checking
AISuggestionCard.propTypes = {
  rubric: PropTypes.object.isRequired,
  onApply: PropTypes.func.isRequired,
  onDismiss: PropTypes.func.isRequired,
};

export default AISuggestionCard;