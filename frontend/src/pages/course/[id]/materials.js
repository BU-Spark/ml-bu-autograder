/**
 * Course Materials Page for BU MET Autograder
 * Handles file uploads, updates, and deletions
 */
import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/router';
import {
  Alert, Box, Button, Card, CardActions, CardContent, Chip, CircularProgress,
  Dialog, DialogActions, DialogContent, DialogTitle, Divider, Grid, IconButton,
  LinearProgress, Link as MuiLink, Paper, Snackbar, TextField, Tooltip, // Added Tooltip
  Typography, useTheme
} from '@mui/material';
import { styled } from '@mui/material/styles';
import {
  ArrowBack as ArrowBackIcon, AttachFile as AttachFileIcon, Delete as DeleteIcon,
  Edit as EditIcon, FilePresent as FileIcon, PictureAsPdf as PdfIcon,
  Description as DocIcon, Slideshow as SlideIcon, FolderZip as ZipIcon,
  InsertDriveFile as GenericFileIcon, CloudUpload as UploadIcon,
} from '@mui/icons-material';
import { useDropzone } from 'react-dropzone';
import { courseService, materialService } from '../../../api'; // Assuming api.js exports these
import CardSkeleton from '../../../components/CardSkeleton';
import ConfirmationDialog from '../../../components/ConfirmationDialog';
import { APP_CONFIG } from '../../../config'; // Assuming config exports APP_CONFIG

// Styled components (kept as before)
const MaterialCard = styled(Card)(({ theme }) => ({ /* ... styles ... */
    height: '100%', display: 'flex', flexDirection: 'column', transition: 'transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out', '&:hover': { transform: 'translateY(-4px)', boxShadow: theme.shadows[6], },
}));
const MaterialCardContent = styled(CardContent)({ /* ... styles ... */
    flexGrow: 1, display: 'flex', flexDirection: 'column', alignItems: 'center',
});
const MaterialCardActions = styled(CardActions)(({ theme }) => ({ /* ... styles ... */
    justifyContent: 'space-between', borderTop: `1px solid ${theme.palette.divider}`, padding: theme.spacing(1),
}));
const FileIconWrapper = styled(Box)(({ theme }) => ({ /* ... styles ... */
    display: 'flex', justifyContent: 'center', marginBottom: theme.spacing(2), fontSize: '3rem',
}));
const DropzoneContainer = styled(Box)(({ theme, isDragActive, isDragAccept, isDragReject }) => ({ /* ... styles ... */
    display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center', padding: theme.spacing(4), borderWidth: 2, borderRadius: theme.shape.borderRadius, borderColor: isDragAccept ? theme.palette.success.main : isDragReject ? theme.palette.error.main : isDragActive ? theme.palette.primary.main : theme.palette.divider, borderStyle: 'dashed', backgroundColor: isDragAccept ? theme.palette.success.lighter : isDragReject ? theme.palette.error.lighter : isDragActive ? theme.palette.action.hover : theme.palette.background.default, color: theme.palette.text.secondary, outline: 'none', transition: 'border .24s ease-in-out, background-color .24s ease-in-out', cursor: 'pointer', minHeight: '150px',
}));
const NoMaterialsBox = styled(Box)(({ theme }) => ({ /* ... styles ... */
    textAlign: 'center', padding: theme.spacing(4), backgroundColor: theme.palette.background.default, borderRadius: theme.shape.borderRadius, marginTop: theme.spacing(4), border: `1px dashed ${theme.palette.divider}`,
}));


export default function CourseMaterials() {
  const router = useRouter();
  const theme = useTheme();
  const { id: courseId, semester} = router.query; // Expecting string values

  // State
  const [materials, setMaterials] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionLoading, setActionLoading] = useState(false); // For CUD operations

  // Upload State
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadFile, setUploadFile] = useState(null);
  const [uploadFormData, setUploadFormData] = useState({ material_name: '', additional_notes: '' });

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
    setAlertMessage(message);
    setAlertSeverity(severity);
    setAlertOpen(true);
  }, []);

  // Generic input handler for simple fields (like text inputs)
  const handleFormInputChange = useCallback((event, formSetter) => {
    const { name, value } = event.target;
    formSetter((prev) => ({ ...prev, [name]: value, }));
  }, []);

  // --- DATA FETCHING ---
  const fetchMaterials = useCallback(async (showLoadingIndicator = true) => {
    console.log("fetchMaterials: Checking context before API call", { courseId, semester });

    if (!courseId || !semester) {
        console.log("fetchMaterials: Missing courseId or semester, skipping API call.");
        // Set appropriate state if skipping
        setLoading(false);
        setMaterials([]);
        return;
    }
    if (showLoadingIndicator) setLoading(true);
    setError(null);
      try {
        console.log(`FETCHING materials for ${courseId}/${semester}`);
        const response = await materialService.getMaterials(semester, courseId); // semester, courseId order
        const materialsData = response?.data; // Extract data

        if (Array.isArray(materialsData)) {
            console.log("RECEIVED materials list:", materialsData);
            setMaterials(materialsData);
        } else {
            console.error("Invalid data received for materials list:", materialsData);
            setMaterials([]);
            setError("Received invalid data format for materials list.");
        }
      } catch (err) {
        console.error('Error fetching materials:', err);
        const errorMsg = err.response?.data?.detail || err.message || 'Failed to load course materials';
        setError(errorMsg);
        setMaterials([]); // Clear materials on error
        // Don't show alert on initial load error, 'error' state handles UI
      } finally {
        if (showLoadingIndicator) setLoading(false);
      }
  }, [courseId, semester]); // Dependencies

  useEffect(() => {
      // Fetch materials when courseId or semester changes
      fetchMaterials(true); // Show loading indicator on mount/context change
  }, [fetchMaterials]);

  // --- FILE UPLOAD LOGIC ---

  const onDrop = useCallback((acceptedFiles) => {
    if (acceptedFiles.length === 0) {
        showAlert('No valid files were dropped or file type not accepted.', 'warning');
        return;
    }
    const file = acceptedFiles[0];
    if (file.size > APP_CONFIG.maxUploadSize) {
      return showAlert(`File size exceeds limit of ${APP_CONFIG.maxUploadSize / (1024 * 1024)}MB`, 'error');
    }
    // No need for explicit type check here if dropzone 'accept' is configured,
    // but keeping it doesn't hurt as a fallback.
    // const fileExtension = file.name.split('.').pop()?.toLowerCase();
    // const fileTypeWithDot = fileExtension ? `.${fileExtension}` : '';
    // if (!fileTypeWithDot || !APP_CONFIG.acceptedFileTypes.materials.includes(fileTypeWithDot)) {
    //    return showAlert(`File type "${fileExtension || 'unknown'}" not supported.`, 'error');
    // }

    setUploadFile(file);
    const fileNameWithoutExt = file.name.substring(0, file.name.lastIndexOf('.')) || file.name;
    setUploadFormData({ material_name: fileNameWithoutExt, additional_notes: '' });
    setUploadDialogOpen(true);
  }, [showAlert]);

  const { getRootProps, getInputProps, isDragActive, isDragAccept, isDragReject } = useDropzone({
    onDrop,
    accept: APP_CONFIG.acceptedFileTypes.materials.reduce((acc, ext) => {
        // This mapping is best-effort for browser filtering
        const mimeTypes = { '.pdf': 'application/pdf', '.doc': 'application/msword', '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', '.ppt': 'application/vnd.ms-powerpoint', '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation', '.txt': 'text/plain', '.zip': 'application/zip' };
        const mime = mimeTypes[ext];
        if (mime) acc[mime] = [ext];
        else acc[ext] = []; // Add extension directly if no known MIME type
        return acc;
    }, {}),
    multiple: false,
    noClick: false, // Allow click to browse
    noKeyboard: true,
  });

  // --- CRUD HANDLERS ---

  const handleUploadMaterial = async () => {
    if (!uploadFile || !uploadFormData.material_name?.trim() || !courseId) {
        showAlert('File, Material Name, Course context are required.', 'warning');
        return;
    }
    setActionLoading(true); // Use generic action loading flag
    setUploadProgress(0);

    try {
        // --- Generate Next Integer ID ---
        // Fetch current materials to find max ID (necessary because POST expects an ID)
        console.log("Fetching current materials to determine next ID...");
        const currentMaterialsResponse = await materialService.getMaterials(semester, courseId);
        const currentMaterials = currentMaterialsResponse?.data;
        let nextId = 0; // Default for first material
        if (Array.isArray(currentMaterials) && currentMaterials.length > 0) {
             const maxId = currentMaterials.reduce((max, mat) => {
                // Try to parse material_id as int, ignore if fails
                const currentIdInt = parseInt(mat.material_id, 10);
                return !isNaN(currentIdInt) && currentIdInt > max ? currentIdInt : max;
             }, -1); // Start comparison from -1
             nextId = maxId + 1;
        }
        console.log(`Determined next material_id: ${nextId}`);
        // --- End ID Generation ---

        // --- Read file ---
        const readFileAsBase64 = (file) => new Promise((resolve, reject) => { /* ... FileReader logic ... */
            const reader = new FileReader();
            reader.onprogress = (event) => { if (event.lengthComputable) setUploadProgress(Math.round((event.loaded / event.total) * 100)); };
            reader.onload = () => resolve(reader.result.split(',')[1]); // Get base64 part
            reader.onerror = (error) => reject(error);
            reader.readAsDataURL(file);
         });
        const base64Data = await readFileAsBase64(uploadFile);
        const fileExtension = uploadFile.name.split('.').pop()?.toLowerCase() ?? '';
        // --- End Read file ---

        const materialPayload = {
            course_id: courseId,
            semester: semester,
            // *** Use the generated integer ID (send as string, backend might convert) ***
            material_id: String(nextId),
            material_name: uploadFormData.material_name.trim(),
            additional_notes: uploadFormData.additional_notes?.trim() || null,
            data: { // Nested data object matching backend model
                data_type: fileExtension,
                content: base64Data,
                metadata: {
                    size: String(uploadFile.size), // Ensure string
                    type: uploadFile.type || 'application/octet-stream',
                    name: uploadFile.name,
                },
            },
        };

        console.log("UPLOADING material with payload:", { ...materialPayload, data: { ...materialPayload.data, content: "..." } }); // Avoid logging large base64
        const response = await materialService.uploadMaterial(materialPayload);
        const uploadedMaterialData = response?.data; // Extract data
        console.log("RESPONSE from uploadMaterial:", response);

        if (!uploadedMaterialData || !uploadedMaterialData.material_id) {
          console.log("RESPONSE from uploadMaterial:", response);
            throw new Error(uploadedMaterialData?.detail || "Invalid response after uploading material.");
        }

        // Add the material returned *from the server* to the state
        setMaterials(prev => [...prev, uploadedMaterialData]);
        showAlert('Material uploaded successfully');
        setUploadDialogOpen(false);
        setUploadFile(null); // Reset file state
        setUploadFormData({ material_name: '', additional_notes: '' }); // Reset form

    } catch (error) {
        console.error('Error uploading material:', error);
        let displayError = 'Failed to upload material.';
        if (error.response) { /* ... detailed error formatting ... */
             const detail = error.response.data?.detail; if (detail) { if (Array.isArray(detail)) { displayError = detail.map(err => `${err.loc?.join('.')} - ${err.msg}`).slice(0, 2).join('; '); if (detail.length > 2) displayError += '...'; } else if (typeof detail === 'string') { displayError = detail; } else { displayError = JSON.stringify(detail); } } else if (error.response.statusText) { displayError = `Error: ${error.response.status} ${error.response.statusText}`; }
        } else if (error.request) { displayError = "Could not contact server."; } else { displayError = error.message || "An unexpected error occurred."; }
        showAlert(displayError, 'error');
    } finally {
        setActionLoading(false); // Use generic loading flag
        setUploadProgress(0);
    }
  };

  const handleUpdateMaterial = async () => {
    if (!editMaterial || !editMaterial.material_id || !editFormData.material_name?.trim() || !courseId || !semester) {
        showAlert('Material context or name is missing.', 'warning');
        return;
    }
    // **IMPORTANT**: Backend PATCH expects the *full* object, including potentially large data field.
    // This is inefficient but required by the current backend endpoint definition.
    const updatedMaterialPayload = {
        // Start with the existing material data from state
        ...editMaterial,
        // Overwrite fields from the form
        material_name: editFormData.material_name.trim(),
        additional_notes: editFormData.additional_notes?.trim() || null,
        // The 'data' field (potentially large) remains from editMaterial
    };
    // Prevent API call if only whitespace changed or nothing changed
    if (updatedMaterialPayload.material_name === editMaterial.material_name &&
        updatedMaterialPayload.additional_notes === editMaterial.additional_notes) {
         console.log("No metadata changes detected, closing edit dialog.");
         setEditDialogOpen(false);
         return;
    }

    setActionLoading(true);
    try {
      console.log(`UPDATING material ${editMaterial.material_id} with payload:`, { ...updatedMaterialPayload, data: { ...updatedMaterialPayload.data, content: "..." } });
      // Call PATCH service
      const response = await materialService.updateMaterial(updatedMaterialPayload);
      const updatedMaterialFromServer = response?.data; // Extract data
      console.log("RESPONSE from updateMaterial:", response);

       if (!updatedMaterialFromServer || !updatedMaterialFromServer.material_id) {
            throw new Error(updatedMaterialFromServer?.detail || "Invalid response after updating material.");
        }

      // Update state with the data returned from the server
      setMaterials(prev => prev.map(m =>
        m.material_id === editMaterial.material_id ? updatedMaterialFromServer : m
      ));
      showAlert('Material updated successfully');
      setEditDialogOpen(false);
      setEditMaterial(null); // Clear edit state

    } catch (error) {
      console.error('Error updating material:', error);
       let displayError = 'Failed to update material.';
       if (error.response) { /* ... detailed error formatting ... */
            const detail = error.response.data?.detail; if (detail) { if (Array.isArray(detail)) { displayError = detail.map(err => `${err.loc?.join('.')} - ${err.msg}`).slice(0, 2).join('; '); if (detail.length > 2) displayError += '...'; } else if (typeof detail === 'string') { displayError = detail; } else { displayError = JSON.stringify(detail); } } else if (error.response.statusText) { displayError = `Error: ${error.response.status} ${error.response.statusText}`; }
       } else if (error.request) { displayError = "Could not contact server."; } else { displayError = error.message || "An unexpected error occurred."; }
      showAlert(displayError, 'error');
    } finally {
        setActionLoading(false);
    }
  };

  const handleDeleteMaterial = async () => {
    const materialObjectToDelete = materialToDelete; // Get from state
    const idToDelete = materialObjectToDelete?.material_id;
    console.log("DELETE request for material ID:", idToDelete);

    if (!idToDelete || !semester || !courseId) {
         showAlert(`Cannot delete: Missing required info.`, 'error');
         console.error("Delete preconditions failed:", { idToDelete, semester, courseId });
         setDeleteDialogOpen(false);
         return;
    }
    setActionLoading(true);
    setDeleteDialogOpen(false); // Close confirmation dialog
    try {
      console.log(`Calling API: deleteMaterial(${semester}, ${courseId}, ${idToDelete})`);
      // Ensure arguments are in the correct order: semester, courseId, materialId
      await materialService.deleteMaterial(semester, courseId, idToDelete);
      console.log(`Material ${idToDelete} reported as deleted by API.`);
      showAlert('Material deleted successfully');
      // Update the list state by filtering out the deleted ID
      setMaterials(prev => prev.filter(m => m.material_id !== idToDelete));
      setMaterialToDelete(null); // Clear the state

    } catch (error) {
      console.error('Error deleting material:', error);
       let displayError = `Failed to delete material (ID: ${idToDelete}).`;
       if (error.response) { /* ... detailed error formatting ... */
             const detail = error.response.data?.detail; if (detail) { if (Array.isArray(detail)) { displayError = detail.map(err => `${err.loc?.join('.')} - ${err.msg}`).slice(0, 2).join('; '); if (detail.length > 2) displayError += '...'; } else if (typeof detail === 'string') { displayError = detail; } else { displayError = JSON.stringify(detail); } } else if (error.response.statusText) { displayError = `Error: ${error.response.status} ${error.response.statusText}`; }
       } else if (error.request) { displayError = "Could not contact server."; } else { displayError = error.message || "An unexpected error occurred."; }
      showAlert(displayError, 'error');
    } finally {
       setActionLoading(false);
    }
  };

  // Dialog Openers
  const openEditDialog = (material) => {
    if (!material || !material.material_id) return;
    setEditMaterial(material);
    setEditFormData({
      material_name: material.material_name || '',
      additional_notes: material.additional_notes || '',
    });
    setEditDialogOpen(true);
  };

  const openDeleteDialog = (material) => {
     if (!material || !material.material_id) return;
     setMaterialToDelete(material);
     setDeleteDialogOpen(true);
  };

  // Helper to get icon based on data_type (extension string)
  const getFileIcon = (extension) => {
    const extLower = extension?.toLowerCase() ?? ''; // Use empty string if null/undefined
    switch (extLower) {
      case 'pdf': return <PdfIcon fontSize="inherit" color="error" />;
      case 'doc': case 'docx': return <DocIcon fontSize="inherit" color="primary" />;
      case 'ppt': case 'pptx': return <SlideIcon fontSize="inherit" color="warning" />;
      case 'txt': return <FileIcon fontSize="inherit" color="info" />;
      case 'zip': return <ZipIcon fontSize="inherit" color="action" />;
      default: return <GenericFileIcon fontSize="inherit" />;
    }
  };

  // --- MAIN RENDER ---
  return (
    <Box sx={{ p: { xs: 1, sm: 2, md: 3 } }}>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <IconButton edge="start" title="Back to Course Overview" onClick={() => router.push(`/course/${courseId}?semester=${semester}`)} sx={{ mr: 1 }} disabled={!courseId || !semester}> <ArrowBackIcon /> </IconButton>
        <Typography variant="h4" component="h1"> Course Materials </Typography>
      </Box>

      {/* Show general fetch error */}
      {error && !loading && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

      {/* Upload Section */}
      <Paper sx={{ p: 3, mb: 4 }}>
        <Typography variant="h6" gutterBottom> Upload New Material </Typography>
        <Typography variant="body2" color="text.secondary" paragraph>
            Drag & drop a file or click below. Max size: {APP_CONFIG.maxUploadSize / (1024 * 1024)}MB. Accepted types: {APP_CONFIG.acceptedFileTypes.materials.join(', ')}.
        </Typography>
        <DropzoneContainer {...getRootProps({ isDragActive, isDragAccept, isDragReject })}>
          <input {...getInputProps()} />
          <UploadIcon sx={{ fontSize: 40, mb: 1, color: isDragAccept ? 'success.main' : isDragReject ? 'error.main' : 'inherit' }} />
          {isDragAccept && <Typography color="success.main">Drop file here!</Typography>}
          {isDragReject && <Typography color="error.main">File type not accepted.</Typography>}
          {!isDragActive && <Typography>Drag & drop file or click to browse</Typography>}
        </DropzoneContainer>
      </Paper>

      {/* Materials List Section */}
      <Typography variant="h5" sx={{ mb: 3 }}> Uploaded Materials </Typography>
      {loading ? ( /* Skeleton Loading */
        <Grid container spacing={3}> {[1, 2, 3, 4].map((item) => <Grid item xs={12} sm={6} md={4} lg={3} key={`skel-${item}`}><CardSkeleton height={220} /></Grid>)} </Grid>
      ) : !Array.isArray(materials) || materials.length === 0 ? ( /* No Materials */
         <NoMaterialsBox><FileIcon sx={{ fontSize: 60, color: 'text.secondary', mb: 2 }} /><Typography variant="h6" gutterBottom>No Materials Found</Typography><Typography color="text.secondary">Upload materials using the section above.</Typography></NoMaterialsBox>
      ) : ( /* Materials Grid */
        <Grid container spacing={3}>
          {materials.map((material) => (
            <Grid item xs={12} sm={6} md={4} lg={3} key={material.material_id}>
              <MaterialCard variant="outlined">
                <MaterialCardContent>
                  <FileIconWrapper> {getFileIcon(material.data?.data_type)} </FileIconWrapper>
                  <Tooltip title={material.material_name}>
                      <Typography variant="h6" component="h2" align="center" noWrap gutterBottom> {material.material_name} </Typography>
                  </Tooltip>
                  <Chip label={(material.data?.data_type || 'unknown').replace('.', '').toUpperCase()} size="small" variant="outlined" sx={{ mb: 1 }} />
                  {material.additional_notes && (
                      <Tooltip title={<Typography sx={{ whiteSpace: 'pre-wrap' }}>{material.additional_notes}</Typography>}>
                         <Typography variant="body2" color="text.secondary" align="center" sx={{ mt: 1, height: '40px', overflow: 'hidden', textOverflow: 'ellipsis', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}>
                             {material.additional_notes}
                         </Typography>
                      </Tooltip>
                   )}
                </MaterialCardContent>
                <MaterialCardActions>
                   {/* Use MuiLink for external links potentially */}
                  <Button size="small" component={MuiLink} href={material.data?.url || '#'} target="_blank" rel="noopener noreferrer" disabled={!material.data?.url || actionLoading}> View </Button>
                  <Box>
                    <Tooltip title="Edit Name/Notes">
                      <IconButton size="small" onClick={() => openEditDialog(material)} disabled={actionLoading}> <EditIcon fontSize="small" /> </IconButton>
                    </Tooltip>
                    <Tooltip title="Delete Material">
                      <IconButton size="small" color="error" onClick={() => openDeleteDialog(material)} disabled={actionLoading}> <DeleteIcon fontSize="small" /> </IconButton>
                    </Tooltip>
                  </Box>
                </MaterialCardActions>
              </MaterialCard>
            </Grid>
          ))}
        </Grid>
      )}

      {/* --- DIALOGS --- */}

      {/* Upload Dialog */}
      <Dialog open={uploadDialogOpen} onClose={() => !actionLoading && setUploadDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Upload New Material</DialogTitle>
        <DialogContent>
           {uploadFile && ( /* Show selected file info */
             <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, p:1, bgcolor: 'action.hover', borderRadius: 1 }}> <Box sx={{ mr: 1.5, fontSize: '1.5rem' }}>{getFileIcon(uploadFile.name.split('.').pop())}</Box> <Box> <Typography variant="body1" fontWeight="medium">{uploadFile.name}</Typography> <Typography variant="caption" color="text.secondary">{(uploadFile.size / 1024).toFixed(1)} KB</Typography> </Box> </Box>
           )}
           {actionLoading && uploadProgress > 0 && ( /* Show progress bar during upload */
             <Box sx={{ width: '100%', my: 2 }}> <LinearProgress variant="determinate" value={uploadProgress} /> <Typography variant="caption" display="block" textAlign="center" sx={{ mt: 0.5 }}> Uploading: {uploadProgress}% </Typography> </Box>
           )}
           <TextField autoFocus name="material_name" label="Material Name" fullWidth value={uploadFormData.material_name} onChange={(e) => handleFormInputChange(e, setUploadFormData)} margin="dense" required disabled={actionLoading} error={!uploadFormData.material_name?.trim()} helperText={!uploadFormData.material_name?.trim() ? 'Name is required' : ''} />
           <TextField name="additional_notes" label="Additional Notes (Optional)" fullWidth multiline rows={3} value={uploadFormData.additional_notes} onChange={(e) => handleFormInputChange(e, setUploadFormData)} margin="dense" disabled={actionLoading} />
        </DialogContent>
        <DialogActions>
           <Button onClick={() => setUploadDialogOpen(false)} disabled={actionLoading}>Cancel</Button>
           <Button onClick={handleUploadMaterial} variant="contained" color="primary" disabled={!uploadFormData.material_name?.trim() || actionLoading} startIcon={actionLoading ? <CircularProgress size={20} color="inherit"/> : <UploadIcon />}> {actionLoading ? 'Uploading...' : 'Confirm Upload'} </Button>
        </DialogActions>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={editDialogOpen} onClose={() => !actionLoading && setEditDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Edit Material Metadata (ID: {editMaterial?.material_id})</DialogTitle>
        <DialogContent>
           {editMaterial && ( /* Show file info */
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, p:1, bgcolor: 'action.hover', borderRadius: 1 }}> <Box sx={{ mr: 1.5, fontSize: '1.5rem' }}>{getFileIcon(editMaterial.data?.data_type)}</Box> <Typography variant="body1" fontWeight="medium">Original Name: {editMaterial.material_name} (.{editMaterial.data?.data_type})</Typography> </Box>
           )}
           <TextField autoFocus name="material_name" label="Material Name" fullWidth value={editFormData.material_name} onChange={(e) => handleFormInputChange(e, setEditFormData)} margin="dense" required disabled={actionLoading} error={!editFormData.material_name?.trim()} helperText={!editFormData.material_name?.trim() ? 'Name is required' : ''} />
           <TextField name="additional_notes" label="Additional Notes (Optional)" fullWidth multiline rows={3} value={editFormData.additional_notes} onChange={(e) => handleFormInputChange(e, setEditFormData)} margin="dense" disabled={actionLoading}/>
        </DialogContent>
        <DialogActions>
           <Button onClick={() => setEditDialogOpen(false)} disabled={actionLoading}>Cancel</Button>
           <Button onClick={handleUpdateMaterial} variant="contained" color="primary" disabled={!editFormData.material_name?.trim() || actionLoading} startIcon={actionLoading ? <CircularProgress size={20} color="inherit"/> : <EditIcon />}> {actionLoading ? 'Saving...' : 'Save Changes'} </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Confirmation */}
      <ConfirmationDialog
        open={deleteDialogOpen}
        onClose={() => !actionLoading && setDeleteDialogOpen(false)}
        title="Delete Material"
        description={`Are you sure you want to permanently delete "${materialToDelete?.material_name ?? 'this material'}" (ID: ${materialToDelete?.material_id})? This cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        confirmColor="error"
        onConfirm={handleDeleteMaterial}
        loading={actionLoading}
      />

      {/* Alert Snackbar */}
      <Snackbar open={alertOpen} autoHideDuration={6000} onClose={() => setAlertOpen(false)} anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}>
        <Alert onClose={() => setAlertOpen(false)} severity={alertSeverity} variant="filled" sx={{ width: '100%' }}> {alertMessage} </Alert>
      </Snackbar>
    </Box>
  );
}