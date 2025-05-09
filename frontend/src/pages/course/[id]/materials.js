/**
 * Course Materials Page for BU MET Autograder
 * Handles file uploads, updates, and deletions.
 * Located at: pages/course/[id]/materials.js
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/router';
import {
  Alert, Box, Button, Card, CardActions, CardContent, Chip, Dialog, DialogActions,
  DialogContent, DialogTitle, Divider, Grid, IconButton, LinearProgress, Link,
  Paper, Snackbar, TextField, Typography, useTheme, CircularProgress // Added CircularProgress
} from '@mui/material';
import { styled } from '@mui/material/styles';
import {
  ArrowBack as ArrowBackIcon, AttachFile as AttachFileIcon, Delete as DeleteIcon,
  Edit as EditIcon, FilePresent as FileIcon, PictureAsPdf as PdfIcon, Description as DocIcon,
  Slideshow as SlideIcon,
  Archive as ZipIcon, InsertDriveFile as GenericFileIcon, CloudUpload as UploadIcon,
} from '@mui/icons-material';
import { useDropzone } from 'react-dropzone';
import { materialService } from '../../../api'; // Correct import
import CardSkeleton from '../../../components/CardSkeleton';
import ConfirmationDialog from '../../../components/ConfirmationDialog';
import { APP_CONFIG } from '../../../config'; // Assuming config path is correct

// Styled components
const MaterialCard = styled(Card)(({ theme }) => ({
    height: '100%', display: 'flex', flexDirection: 'column', transition: 'transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out', '&:hover': { transform: 'translateY(-4px)', boxShadow: theme.shadows[6] }
}));
const MaterialCardContent = styled(CardContent)({
    flexGrow: 1 // Ensure content takes available space
});
const MaterialCardActions = styled(CardActions)(({ theme }) => ({
    justifyContent: 'space-between', borderTop: `1px solid ${theme.palette.divider}`, padding: theme.spacing(1) // Adjusted padding
}));
const FileIconWrapper = styled(Box)(({ theme }) => ({
    display: 'flex', justifyContent: 'center', alignItems: 'center', marginBottom: theme.spacing(2), minHeight: 60 // Give icon area some height
}));
const DropzoneContainer = styled(Box)(({ theme, isDragActive, isDragAccept, isDragReject }) => ({
  display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: theme.spacing(4), borderWidth: 2, borderRadius: theme.shape.borderRadius, borderColor: isDragAccept ? theme.palette.success.main : isDragReject ? theme.palette.error.main : isDragActive ? theme.palette.primary.main : theme.palette.divider, borderStyle: 'dashed', backgroundColor: isDragActive ? theme.palette.action.hover : theme.palette.background.default, color: theme.palette.text.primary, outline: 'none', transition: 'border .24s ease-in-out', cursor: 'pointer', textAlign: 'center'
}));
const NoMaterialsBox = styled(Box)(({ theme }) => ({
    textAlign: 'center', padding: theme.spacing(4), backgroundColor: theme.palette.background.default, borderRadius: theme.shape.borderRadius, marginTop: theme.spacing(4), border: `1px dashed ${theme.palette.divider}`
}));


// Main component
export default function CourseMaterialsPage() {
  const router = useRouter();
  const theme = useTheme();
  const { id: courseIdParam, semester: semesterParam } = router.query;
  const courseId = typeof courseIdParam === 'string' ? courseIdParam : null;
  const semester = typeof semesterParam === 'string' ? semesterParam : null;

  // State
  const [materials, setMaterials] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);

  // Upload State
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadFile, setUploadFile] = useState(null);
  const [uploadFormData, setUploadFormData] = useState({ material_id: '', additional_notes: '' });

  // Edit State
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editMaterial, setEditMaterial] = useState(null);
  const [editFormData, setEditFormData] = useState({ material_name: '', additional_notes: '' });

  // Delete State
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [materialToDelete, setMaterialToDelete] = useState(null);

  // Alert State
  const [alertOpen, setAlertOpen] = useState(false);
  const [alertMessage, setAlertMessage] = useState('');
  const [alertSeverity, setAlertSeverity] = useState('success');

  // --- UTILITY FUNCTIONS ---
  const showAlert = useCallback((message, severity = 'success') => {
    setAlertMessage(message); setAlertSeverity(severity); setAlertOpen(true);
  }, []);

  const formatApiError = (error, defaultMessage) => {
    let displayError = defaultMessage;
    if (error.response) { const detail = error.response.data?.detail; if (detail) { if (Array.isArray(detail)) { displayError = detail.map(err => `${err.loc?.join('.')} - ${err.msg}`).slice(0, 3).join('; '); if (detail.length > 3) displayError += '...'; } else if (typeof detail === 'string') { displayError = detail; } else { try { displayError = JSON.stringify(detail); } catch { /* ignore */ } } } else if (error.response.statusText) { displayError = `Error: ${error.response.status} ${error.response.statusText}`; } }
    else if (error.request) { displayError = "Network Error: Could not contact server."; }
    else if (error.message) { displayError = error.message; }
    return displayError || defaultMessage;
  };

  // --- DATA FETCHING ---
  const fetchMaterials = useCallback(async () => {
      if (!courseId || !semester) return;
      setLoading(true); setError(null);
      try {
        console.log(`FETCHING materials for ${courseId}/${semester}`);
        const materialsData = await materialService.getMaterials({ course_id: courseId, semester: semester });

        if (Array.isArray(materialsData)) {
            console.log("RECEIVED materials list:", materialsData);
             // Validate structure slightly - ensure data exists
             const validMaterials = materialsData.filter(m => m && m.material_id && m.data && m.data.data_type && m.data.uri);
             if (validMaterials.length !== materialsData.length) { console.warn("Some items in the fetched materials list were invalid:", materialsData); }
            // Augment with local display name if needed, defaulting to material_id
            setMaterials(validMaterials.map(m => ({...m, material_name: m.material_name || m.material_id})));
        } else {
            console.error("Invalid data received for materials list (expected array):", materialsData);
            setMaterials([]); setError("Received invalid data format for materials list.");
        }
      } catch (err) {
        console.error("Error fetching materials list:", err);
        setError(formatApiError(err, 'Failed to load course materials.'));
        setMaterials([]);
      } finally { setLoading(false); }
  }, [courseId, semester]); // Correct dependencies

  useEffect(() => {
    if (router.isReady) {
        if (courseId && semester) { fetchMaterials(); }
        else { setError("Course ID or Semester is missing from URL."); setLoading(false); }
    }
  }, [router.isReady, courseId, semester, fetchMaterials]);

  // --- FILE HANDLING & UPLOAD ---
  const onDrop = useCallback((acceptedFiles, rejectedFiles) => {
     if (rejectedFiles && rejectedFiles.length > 0) {
        const firstError = rejectedFiles[0].errors[0];
        if (firstError.code === 'file-too-large') { showAlert(`File size exceeds ${APP_CONFIG.maxUploadSize / (1024 * 1024)}MB limit.`, 'error'); }
        else if (firstError.code === 'file-invalid-type') { showAlert(`File type not supported. Accepted: ${APP_CONFIG.acceptedFileTypes.materials.join(', ')}`, 'error'); }
        else { showAlert(`File error: ${firstError.message}`, 'error'); }
        return;
    }
    if (acceptedFiles.length === 0) return;
    const file = acceptedFiles[0];
    setUploadFile(file);
    const fileNameWithoutExt = file.name.substring(0, file.name.lastIndexOf('.')) || file.name;
    setUploadFormData({
      material_id: fileNameWithoutExt.replace(/[^a-zA-Z0-9-_.]/g, '_'),
      additional_notes: '',
    });
    setUploadDialogOpen(true);
  }, [showAlert]); // Use showAlert from useCallback

  const { getRootProps, getInputProps, isDragActive, isDragAccept, isDragReject } = useDropzone({
    onDrop,
    accept: APP_CONFIG.acceptedFileTypes.materials.reduce((acc, ext) => {
      const mimeTypes = {'.pdf': 'application/pdf', '.doc': 'application/msword', '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', '.ppt': 'application/vnd.ms-powerpoint', '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation', '.txt': 'text/plain', '.zip': 'application/zip' };
      const mimeType = mimeTypes[ext] || '*/*';
      acc[mimeType] = [ext];
      return acc;
    }, {}),
    maxSize: APP_CONFIG.maxUploadSize,
    multiple: false,
  });

  const handleUploadMaterial = async () => {
    if (!uploadFile || !uploadFormData.material_id || !courseId || !semester) return showAlert("Missing file, material ID, or course context.", "warning");
    if (!/^[a-zA-Z0-9-_.]+$/.test(uploadFormData.material_id)) return showAlert("Material ID can only contain letters, numbers, hyphens (-), underscores (_), and periods (.).", "warning");
    setActionLoading(true); setUploadProgress(0);
    try {
      const reader = new FileReader();
      reader.onload = async (event) => {
          try {
              if (!event.target?.result || typeof event.target.result !== 'string') throw new Error("File could not be read or result is invalid.");
              const base64Data = event.target.result.split(',')[1];
              if (typeof base64Data === 'undefined') throw new Error("Could not extract base64 data.");
              const mimeType = uploadFile.type || 'application/octet-stream';
              const materialPayload = { semester: semester, course_id: courseId, material_id: uploadFormData.material_id.trim(), data: { data_type: mimeType, content: base64Data } };
              console.log("Uploading material with payload:", { ...materialPayload, data: { ...materialPayload.data, content: '...base64...' } });
              const result = await materialService.uploadMaterial(materialPayload);
              if (result && result.material_id && result.data?.uri) {
                   await fetchMaterials(); // Refetch the entire list after successful upload
                   showAlert('Material uploaded successfully');
              } else { throw new Error("Invalid response after upload."); }
              setUploadFile(null); setUploadFormData({ material_id: '', additional_notes: '' }); setUploadDialogOpen(false);
          } catch (uploadError) { console.error('Error during material upload API call:', uploadError); showAlert(formatApiError(uploadError, 'Failed to upload material.'), 'error');
          } finally { setActionLoading(false); setUploadProgress(100); } // Might need adjustment if upload is truly async
      };
      reader.onerror = () => { setActionLoading(false); showAlert('Error reading file.', 'error'); };
      reader.readAsDataURL(uploadFile);
    } catch (error) { console.error('Error setting up file reader:', error); showAlert(formatApiError(error, 'Failed to initiate upload.'), 'error'); setActionLoading(false); }
  };


  // --- MATERIAL EDIT / DELETE ---
  const openEditDialog = (material) => {
    if (!material || !material.material_id) return;
    setEditMaterial(material);
    setEditFormData({ material_name: material.material_name || material.material_id, additional_notes: material.additional_notes || '', });
    setEditDialogOpen(true);
  };

  const handleUpdateMaterial = async () => {
    if (!editMaterial) return;
    const updatedMaterialLocally = { ...editMaterial, material_name: editFormData.material_name.trim(), additional_notes: editFormData.additional_notes?.trim() || null };
    setMaterials(prev => prev.map(m => m.material_id === editMaterial.material_id ? updatedMaterialLocally : m));
    setEditDialogOpen(false);
    showAlert('Material info updated locally (API update for name/notes not available).', 'warning');
  };

  const openDeleteDialog = (material) => { if (!material || !material.material_id) return; setMaterialToDelete(material); setDeleteDialogOpen(true); }

  const handleDeleteMaterial = async () => {
    if (!materialToDelete || !courseId || !semester) return;
    const idToDelete = materialToDelete.material_id;
    const nameToDelete = materialToDelete.material_name || idToDelete;
    setActionLoading(true); setDeleteDialogOpen(false);
    try {
      await materialService.deleteMaterial({ course_id: courseId, semester: semester, material_id: idToDelete });
      setMaterials(prev => prev.filter(m => m.material_id !== idToDelete));
      showAlert(`Material "${nameToDelete}" deleted.`);
    } catch (error) { console.error('Error deleting material:', error); showAlert(formatApiError(error, 'Failed to delete material.'), 'error');
    } finally { setMaterialToDelete(null); setActionLoading(false); }
  };

  // --- RENDER LOGIC ---
  const getFileIcon = (dataTypeObject) => {
    // *** CORRECTED: Access the 'extension' attribute (or similar) ***
    // *** Make sure 'extension' is the correct attribute name on your DataType object ***
    const extension = dataTypeObject?.extension;

    if (typeof extension !== 'string') {
        console.warn("getFileIcon received invalid dataTypeObject or missing extension:", dataTypeObject);
        return <GenericFileIcon fontSize="large" />; // Fallback
    }

    switch (extension.toLowerCase()) { // Now safely calling toLowerCase on the string
      case 'pdf': return <PdfIcon fontSize="large" color="error" />;
      case 'doc': return <DocIcon fontSize="large" color="primary" />;
      case 'docx': return <DocIcon fontSize="large" color="primary" />;
      case 'ppt': return <SlideIcon fontSize="large" color="warning" />;
      case 'pptx': return <SlideIcon fontSize="large" color="warning" />;
      case 'txt': return <FileIcon fontSize="large" color="info" />;
      case 'zip': return <ZipIcon fontSize="large" color="action" />;
      // Add more cases based on your DataType.extension possibilities
      default: return <GenericFileIcon fontSize="large" />;
    }
  };

  // --- MAIN RETURN JSX ---
  return (
    <Box sx={{ p: { xs: 1, sm: 2, md: 3 } }}>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3, flexWrap: 'wrap', gap: 1 }}>
        <IconButton title="Back to Course Overview" aria-label="back" onClick={() => (courseId && semester) && router.push(`/course/${courseId}?semester=${semester}`)} disabled={!courseId || !semester || actionLoading} sx={{ mr: 1 }}> <ArrowBackIcon /> </IconButton>
        <Typography variant="h4" component="h1" sx={{ flexGrow: 1, mr: 1 }}>Course Materials</Typography>
        <Button variant="contained" color="primary" size="small" startIcon={<UploadIcon />} onClick={() => document.getElementById('file-input-button')?.click()} disabled={actionLoading || !courseId || !semester}> Upload Material </Button>
         <input {...getInputProps()} style={{ display: 'none' }} id="file-input-button"/>
      </Box>

      {/* Main Error Alert */}
      {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

      {/* Dropzone Area */}
      <Paper sx={{ p: { xs: 1.5, sm: 2 }, mb: 4 }}>
        <Typography variant="h6" gutterBottom>Upload New Material</Typography>
        <Typography variant="body2" color="text.secondary" paragraph>Drag & drop or browse. Max size: {APP_CONFIG.maxUploadSize / (1024 * 1024)}MB. Allowed types: {APP_CONFIG.acceptedFileTypes.materials.join(', ')}</Typography>
        <DropzoneContainer {...getRootProps()} isDragActive={isDragActive} isDragAccept={isDragAccept} isDragReject={isDragReject}>
          <input {...getInputProps()} />
          <UploadIcon sx={{ fontSize: 48, mb: 2, color: 'action.active' }} />
          <Typography variant="body1">{isDragActive ? 'Drop the file here...' : 'Drag & drop file, or click to browse'}</Typography>
        </DropzoneContainer>
      </Paper>

      {/* Materials List Section */}
      <Typography variant="h5" sx={{ mb: 3 }}>All Materials</Typography>
      {loading ? (
          <Grid container spacing={3}>{[1, 2, 3, 4].map((i) => <Grid item xs={12} sm={6} md={4} lg={3} key={`skel-${i}`}><CardSkeleton height={200} /></Grid>)}</Grid>
      ) : !materials.length ? (
          <NoMaterialsBox><FileIcon sx={{ fontSize: 60, color: 'text.secondary', mb: 2 }} /><Typography variant="h6">No Materials Found</Typography><Typography color="text.secondary" sx={{ mb: 2 }}>Upload materials using the area above.</Typography></NoMaterialsBox>
      ) : (
        <Grid container spacing={3}>
          {materials.map((material) => (
            material?.material_id && material?.data?.uri && material?.data?.data_type ? (
                <Grid item xs={12} sm={6} md={4} lg={3} key={material.material_id}>
                <MaterialCard variant='outlined'>
                    <MaterialCardContent>
                    {/* *** CORRECTED: Pass the DataType object to getFileIcon *** */}
                    <FileIconWrapper>{getFileIcon(material.data.data_type)}</FileIconWrapper>
                    <Typography variant="h6" component="h2" align="center" noWrap gutterBottom title={material.material_id}>{material.material_name || material.material_id}</Typography>{/* Use material_name */}
                    <Box sx={{ textAlign: 'center', mb: 1 }}>
                        {/* *** CORRECTED: Get extension from DataType object *** */}
                        {/* *** ACTION NEEDED: Verify 'extension' attribute name *** */}
                        <Chip label={(material.data.data_type?.extension || 'file').toUpperCase()} size="small" variant="outlined" />
                    </Box>
                    {material.additional_notes && ( <Typography variant="body2" color="text.secondary" sx={{ mt: 1, textAlign: 'center', overflow: 'hidden', textOverflow: 'ellipsis', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}> {material.additional_notes} </Typography> )}
                    </MaterialCardContent>
                    <MaterialCardActions>
                    <Button size="small" component={Link} href={material.data.uri} target="_blank" rel="noopener noreferrer" disabled={!material.data.uri}> View </Button>
                    <Box>
                        <IconButton title="Edit Material Info (Local)" size="small" color="primary" onClick={() => openEditDialog(material)} disabled={actionLoading}><EditIcon fontSize="small" /></IconButton>
                        <IconButton title="Delete Material" size="small" color="error" onClick={() => openDeleteDialog(material)} disabled={actionLoading}><DeleteIcon fontSize="small" /></IconButton>
                    </Box>
                    </MaterialCardActions>
                </MaterialCard>
                </Grid>
            ) : null
          ))}
        </Grid>
      )}

      {/* Dialogs and Snackbar */}
      <Dialog open={uploadDialogOpen} onClose={() => !actionLoading && setUploadDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Upload Material Details</DialogTitle>
        <DialogContent>
          {actionLoading && <Box sx={{ width: '100%', mb: 2 }}><LinearProgress /></Box>}
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, p: 1, bgcolor: 'action.hover', borderRadius: 1 }}>
             {/* Use getFileIcon with the file's MIME type for preview */}
            {getFileIcon(uploadFile?.type || '')}
            <Box sx={{ ml: 1.5, overflow: 'hidden' }}>
                <Typography variant="body1" noWrap> {uploadFile?.name}</Typography>
                {uploadFile?.size && <Typography variant="caption" color="text.secondary">{(uploadFile.size / 1024).toFixed(1)} KB</Typography>}
            </Box>
          </Box>
          <TextField autoFocus name="material_id" label="Material ID / Name" fullWidth value={uploadFormData.material_id} onChange={(e) => handleInputChange(e, setUploadFormData)} margin="dense" required error={!uploadFormData.material_id?.trim() && uploadFormData.material_id !== ''} helperText={!uploadFormData.material_id?.trim() && uploadFormData.material_id !== '' ? "Required. Use letters, numbers, -, _, ." : "Unique identifier for this material"} disabled={actionLoading} />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setUploadDialogOpen(false)} disabled={actionLoading}>Cancel</Button>
          <Button onClick={handleUploadMaterial} variant="contained" color="primary" disabled={!uploadFormData.material_id?.trim() || actionLoading} startIcon={actionLoading ? <CircularProgress size={20} color="inherit"/> : <UploadIcon />}> {actionLoading ? 'Uploading...' : 'Upload'} </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={editDialogOpen} onClose={() => !actionLoading && setEditDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Edit Material Info (Local Only)</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{mb: 2}}>Material ID: {editMaterial?.material_id ?? 'N/A'}</Typography>
          <TextField autoFocus name="material_name" label="Display Name (Local Edit)" fullWidth value={editFormData.material_name} onChange={(e) => handleInputChange(e, setEditFormData)} margin="dense" required error={!editFormData.material_name?.trim()} helperText={!editFormData.material_name?.trim() ? "Required" : "This name is only for display"} disabled={actionLoading}/>
          <TextField name="additional_notes" label="Additional Notes (Local Edit)" fullWidth multiline rows={3} value={editFormData.additional_notes} onChange={(e) => handleInputChange(e, setEditFormData)} margin="dense" disabled={actionLoading}/>
           <Alert severity="warning" sx={{mt: 2}}>Note: Changes to name and notes are currently only saved locally in this view. The API does not support updating these fields.</Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditDialogOpen(false)} disabled={actionLoading}>Cancel</Button>
          <Button onClick={handleUpdateMaterial} variant="contained" color="primary" disabled={actionLoading || !editFormData.material_name?.trim()}>{actionLoading ? <CircularProgress size={24}/> : 'Save Local Changes'}</Button>
        </DialogActions>
      </Dialog>

      <ConfirmationDialog open={deleteDialogOpen} onClose={() => !actionLoading && setDeleteDialogOpen(false)} onConfirm={handleDeleteMaterial} title="Delete Material?" description={`Permanently delete material "${materialToDelete?.material_name || materialToDelete?.material_id || ''}"?`} confirmText="Delete" cancelText="Cancel" confirmColor="error" loading={actionLoading}/>

      <Snackbar open={alertOpen} autoHideDuration={6000} onClose={() => setAlertOpen(false)} anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}>
        <Alert onClose={() => setAlertOpen(false)} severity={alertSeverity} variant="filled" sx={{ width: '100%' }}> {alertMessage} </Alert>
      </Snackbar>
    </Box>
  );
}