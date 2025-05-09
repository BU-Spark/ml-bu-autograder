/**
 * Grading Mode Select Component for BU MET Autograder
 * Dropdown component for selecting grading modes
 */

import React from 'react';
import {
  FormControl,
  FormHelperText,
  InputLabel,
  MenuItem,
  Select,
  Tooltip,
  Typography,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import {
  Assignment as AssignmentIcon,
  AssignmentTurnedIn as GradedIcon,
  AssignmentLate as UngradedIcon,
  People as SpecificIcon,
} from '@mui/icons-material';
import PropTypes from 'prop-types';

// Styled components
const StyledMenuItem = styled(MenuItem)(({ theme }) => ({
  display: 'flex',
  alignItems: 'center',
  gap: theme.spacing(1),
}));

// Grading mode descriptions
const modeDescriptions = {
  ungraded: 'Grade all ungraded responses for the selected assignment or question',
  all: 'Grade or regrade all responses (will overwrite existing grades)',
  specific: 'Grade only selected student responses',
};

// Grading Mode Select component
const GradingModeSelect = ({ value, onChange, disabled = false }) => {
  return (
    <FormControl fullWidth variant="outlined">
      <InputLabel id="grading-mode-select-label">Grading Mode</InputLabel>
      <Select
        labelId="grading-mode-select-label"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        label="Grading Mode"
        disabled={disabled}
      >
        <StyledMenuItem value="ungraded">
          <UngradedIcon color="warning" />
          <Typography variant="body2">Ungraded Responses</Typography>
        </StyledMenuItem>

        <StyledMenuItem value="all">
          <GradedIcon color="primary" />
          <Typography variant="body2">All Responses</Typography>
        </StyledMenuItem>

        <StyledMenuItem value="specific">
          <SpecificIcon color="info" />
          <Typography variant="body2">Specific Students</Typography>
        </StyledMenuItem>
      </Select>

      <Tooltip title={modeDescriptions[value] || ''} placement="right">
        <FormHelperText>{modeDescriptions[value]}</FormHelperText>
      </Tooltip>
    </FormControl>
  );
};

// PropTypes for type checking
GradingModeSelect.propTypes = {
  value: PropTypes.oneOf(['ungraded', 'all', 'specific']).isRequired,
  onChange: PropTypes.func.isRequired,
  disabled: PropTypes.bool,
};

export default GradingModeSelect;