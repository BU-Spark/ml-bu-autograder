/**
 * Confirmation Dialog Component for BU MET Autograder
 * Reusable dialog for confirming user actions
 */

import React from 'react';
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
} from '@mui/material';
import PropTypes from 'prop-types';

// Confirmation dialog component
export default function ConfirmationDialog({
  open,
  title,
  message,
  confirmText,
  cancelText,
  onConfirm,
  onCancel,
  confirmButtonProps = {},
}) {
  return (
    <Dialog
      open={open}
      onClose={onCancel}
      aria-labelledby="alert-dialog-title"
      aria-describedby="alert-dialog-description"
      maxWidth="sm"
      fullWidth
    >
      <DialogTitle id="alert-dialog-title">{title}</DialogTitle>
      <DialogContent>
        <DialogContentText id="alert-dialog-description">
          {message}
        </DialogContentText>
      </DialogContent>
      <DialogActions>
        <Button onClick={onCancel}>{cancelText || 'Cancel'}</Button>
        <Button
          onClick={onConfirm}
          variant="contained"
          autoFocus
          {...confirmButtonProps}
        >
          {confirmText || 'Confirm'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

// PropTypes for type checking
ConfirmationDialog.propTypes = {
  open: PropTypes.bool.isRequired,
  title: PropTypes.string.isRequired,
  message: PropTypes.string.isRequired,
  confirmText: PropTypes.string,
  cancelText: PropTypes.string,
  onConfirm: PropTypes.func.isRequired,
  onCancel: PropTypes.func.isRequired,
  confirmButtonProps: PropTypes.object,
};