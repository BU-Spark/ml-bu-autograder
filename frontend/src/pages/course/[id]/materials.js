/**
 * Course Materials Page for BU MET Autograder
 * Handles file uploads, updates, and deletions
 */
import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/router';
import {
  Alert, Box, Button, Card, CardActions, CardContent, Chip, CircularProgress,
  Dialog, DialogActions, DialogContent, DialogTitle, Divider, Grid, IconButton,
  LinearProgress, Link as MuiLink, Paper, Snackbar, TextField, Tooltip,
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

// Styled components
const MaterialCard = styled(Card)(({ theme }) => ({
    height: '100%', display: 'flex', flexDirection: 'column', transition: 'transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out', '&:hover': { transform: 'translateY(-4px)', boxShadow: theme.shadows[6], },
}));
const MaterialCardContent = styled(CardContent)({
    flexGrow: 1, display: 'flex', flexDirection: 'column', alignItems: 'center',
});
const MaterialCardActions = styled(CardActions)(({ theme }) => ({
    justifyContent: 'space-between', borderTop: `1px solid ${theme.palette.divider}`, padding: theme.spacing(1),
}));
const FileIconWrapper = styled(Box)(({ theme }) => ({
    display: 'flex', justifyContent: 'center', marginBottom: theme.spacing(2), fontSize: '3rem',
}));
const DropzoneContainer = styled(Box)(({ theme, isDragActive, isDragAccept, isDragReject }) => ({
    display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center', padding: theme.spacing(4), borderWidth: 2, borderRadius: theme.shape.borderRadius, borderColor: isDragAccept ? theme.palette.success.main : isDragReject ? theme.palette.error.main : isDragActive ? theme.palette.primary.main : theme.palette.divider, borderStyle: 'dashed', backgroundColor: isDragAccept ? theme.palette.success.lighter : isDragReject ? theme.palette.error.lighter : isDragActive ? theme.palette.action.hover : theme.palette.background.default, color: theme.palette.text.secondary, outline: 'none', transition: 'border .24s ease-in-out, background-color .24s ease-in-out', cursor: 'pointer', minHeight: '150px',
}));
const NoMaterialsBox = styled(Box)(({ theme }) => ({
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

  // Format API errors for display
  const formatApiError = useCallback((err, defaultMessage) => {
    console.error("API Error:", err); // Log the full error
    if (err?.response?.data?.detail) {
        if (Array.isArray(err.response.data.detail)) {
            // Handle FastAPI validation errors array
            return err.response.data.detail.map(d => `${d.loc?.join('.') || 'error'}: ${d.msg}`).join('; ');
        }
        return err.response.data.detail; // Return detail string directly
    }
    if (err?.message) {
      return err.message; // Axios error message or custom Error message
    }
    return defaultMessage; // Fallback message
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
        setLoading(false);
        setMaterials([]);
        setError(null); // Clear previous errors if context is missing
        return;
    }
    if (showLoadingIndicator) setLoading(true);
    setError(null);
      try {
        console.log(`FETCHING materials for ${courseId}/${semester}`);
        const response = await materialService.getMaterials(semester, courseId); // semester, courseId order
        const materialsData = response?.data;

        if (Array.isArray(materialsData)) {
            console.log("RECEIVED materials list:", materialsData);
            // Sort materials by ID (assuming integer IDs now) for consistent order
            const sortedMaterials = materialsData.sort((a, b) => {
                const idA = parseInt(a.material_id, 10);
                const idB = parseInt(b.material_id, 10);
                if (isNaN(idA) || isNaN(idB)) return 0; // Keep original order if IDs aren't numeric
                return idA - idB;
            });
            setMaterials(sortedMaterials);
        } else {
            console.error("Invalid data received for materials list:", materialsData);
            setMaterials([]);
            setError("Received invalid data format for materials list.");
        }
      } catch (err) {
        console.error('Error fetching materials:', err);
        const errorMsg = formatApiError(err, 'Failed to load course materials');
        setError(errorMsg);
        setMaterials([]); // Clear materials on error
      } finally {
        if (showLoadingIndicator) setLoading(false);
      }
  // Dependencies include formatApiError now
  }, [courseId, semester, formatApiError]);

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

    setUploadFile(file);
    const fileNameWithoutExt = file.name.substring(0, file.name.lastIndexOf('.')) || file.name;
    setUploadFormData({ material_name: fileNameWithoutExt, additional_notes: '' });
    setUploadDialogOpen(true);
  }, [showAlert]);

  const { getRootProps, getInputProps, isDragActive, isDragAccept, isDragReject } = useDropzone({
    onDrop,
    accept: APP_CONFIG.acceptedFileTypes.materials.reduce((acc, ext) => {
        const mimeTypes = { '.pdf': 'application/pdf', '.doc': 'application/msword', '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', '.ppt': 'application/vnd.ms-powerpoint', '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation', '.txt': 'text/plain', '.zip': 'application/zip' };
        const mime = mimeTypes[ext];
        if (mime) acc[mime] = [ext];
        else acc[ext] = [];
        return acc;
    }, {}),
    multiple: false,
    noClick: false,
    noKeyboard: true,
  });

  // --- CRUD HANDLERS ---

  const handleUploadMaterial = async () => {
    if (!uploadFile || !uploadFormData.material_name?.trim() || !courseId || !semester) { // Added semester check
        showAlert('File, Material Name, Course context are required.', 'warning');
        return;
    }
    setActionLoading(true);
    setUploadProgress(0);

    try {
        // --- REMOVED Frontend ID Generation ---
        // console.log("Fetching current materials to determine next ID...");
        // ... (code to fetch and calculate nextId) ...
        // --- END REMOVED ID Generation ---

        // --- Read file ---
        const readFileAsBase64 = (file) => new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onprogress = (event) => { if (event.lengthComputable) setUploadProgress(Math.round((event.loaded / event.total) * 100)); };
            reader.onload = () => {
                 // Ensure result is string and split correctly
                 if (typeof reader.result === 'string') {
                     const base64Part = reader.result.split(',')[1];
                     if (base64Part) {
                         resolve(base64Part);
                     } else {
                         reject(new Error("Could not extract base64 data from FileReader result."));
                     }
                 } else {
                     reject(new Error("FileReader result was not a string."));
                 }
             };
            reader.onerror = (error) => reject(error);
            reader.readAsDataURL(file);
         });

        const base64Data = await readFileAsBase64(uploadFile);
        const fileExtension = uploadFile.name.split('.').pop()?.toLowerCase() ?? '';
        // --- End Read file ---

        // Construct payload WITHOUT material_id
        const materialPayload = {
            course_id: courseId,
            semester: semester,
            // material_id: String(nextId), // <<<--- REMOVED
            material_name: uploadFormData.material_name.trim(),
            additional_notes: uploadFormData.additional_notes?.trim() || null,
            data: {
                data_type: fileExtension,
                content: base64Data,
                metadata: {
                    size: String(uploadFile.size),
                    type: uploadFile.type || 'application/octet-stream',
                    name: uploadFile.name,
                },
            },
        };

        console.log("UPLOADING material payload (without material_id):", { ...materialPayload, data: { ...materialPayload.data, content: "..." } }); // Avoid logging large base64
        const response = await materialService.uploadMaterial(materialPayload);
        const uploadedMaterialData = response?.data;
        console.log("RESPONSE from uploadMaterial:", response);

        // Check if the response contains the generated material_id
        if (!uploadedMaterialData || typeof uploadedMaterialData.material_id === 'undefined') { // Check for presence of material_id
          console.error("Invalid response structure from uploadMaterial:", uploadedMaterialData);
          throw new Error(uploadedMaterialData?.detail || "Invalid response after uploading material (missing material_id).");
        }

        // Add the material returned *from the server* (now including the generated ID)
        setMaterials(prev => [...prev, uploadedMaterialData].sort((a, b) => { // Sort after adding
            const idA = parseInt(a.material_id, 10);
            const idB = parseInt(b.material_id, 10);
            if (isNaN(idA) || isNaN(idB)) return 0;
            return idA - idB;
        }));
        showAlert(`Material '${uploadedMaterialData.material_name}' uploaded successfully (ID: ${uploadedMaterialData.material_id})`);
        setUploadDialogOpen(false);
        setUploadFile(null);
        setUploadFormData({ material_name: '', additional_notes: '' });

    } catch (error) {
        // Use the improved error formatting
        const displayError = formatApiError(error, 'Failed to upload material.');
        showAlert(displayError, 'error');
    } finally {
        setActionLoading(false);
        setUploadProgress(0);
    }
  };

  const handleUpdateMaterial = async () => {
    if (!editMaterial || typeof editMaterial.material_id === 'undefined' || !editFormData.material_name?.trim() || !courseId || !semester) {
        showAlert('Material context or name is missing.', 'warning');
        return;
    }

    // Construct the full payload as expected by PATCH /course_material
    const updatedMaterialPayload = {
        ...editMaterial, // Start with existing data (includes ID, semester, course_id, data)
        material_name: editFormData.material_name.trim(), // Overwrite name
        additional_notes: editFormData.additional_notes?.trim() || null, // Overwrite notes
    };

    // Prevent API call if only whitespace changed or nothing changed
    if (updatedMaterialPayload.material_name === editMaterial.material_name &&
        updatedMaterialPayload.additional_notes === (editMaterial.additional_notes || null)) { // Compare with null if original was empty
         console.log("No metadata changes detected, closing edit dialog.");
         setEditDialogOpen(false);
         return;
    }

    setActionLoading(true);
    try {
      console.log(`UPDATING material ${editMaterial.material_id} with payload:`, { ...updatedMaterialPayload, data: { ...updatedMaterialPayload.data, content: "..." } });
      const response = await materialService.updateMaterial(updatedMaterialPayload);
      const updatedMaterialFromServer = response?.data;
      console.log("RESPONSE from updateMaterial:", response);

       if (!updatedMaterialFromServer || typeof updatedMaterialFromServer.material_id === 'undefined') {
            throw new Error(updatedMaterialFromServer?.detail || "Invalid response after updating material.");
        }

      // Update state with the data returned from the server
      setMaterials(prev => prev.map(m =>
        m.material_id === editMaterial.material_id ? updatedMaterialFromServer : m
      ));
      showAlert('Material updated successfully');
      setEditDialogOpen(false);
      setEditMaterial(null);

    } catch (error) {
      const displayError = formatApiError(error, 'Failed to update material.');
      showAlert(displayError, 'error');
    } finally {
        setActionLoading(false);
    }
  };

  const handleDeleteMaterial = async () => {
    const materialObjectToDelete = materialToDelete;
    const idToDelete = materialObjectToDelete?.material_id;

    if (typeof idToDelete === 'undefined' || !semester || !courseId) { // Check type of ID
         showAlert(`Cannot delete: Missing required info (ID: ${idToDelete}, Semester: ${semester}, Course: ${courseId}).`, 'error');
         console.error("Delete preconditions failed:", { idToDelete, semester, courseId });
         setDeleteDialogOpen(false);
         return;
    }
    setActionLoading(true);
    setDeleteDialogOpen(false);
    try {
      console.log(`Calling API: deleteMaterial(${semester}, ${courseId}, ${idToDelete})`);
      await materialService.deleteMaterial(semester, courseId, idToDelete); // Pass ID as number/string as expected by API
      console.log(`Material ${idToDelete} reported as deleted by API.`);
      showAlert('Material deleted successfully');
      setMaterials(prev => prev.filter(m => m.material_id !== idToDelete)); // Strict comparison might be needed if types differ
      setMaterialToDelete(null);

    } catch (error) {
       const displayError = formatApiError(error, `Failed to delete material (ID: ${idToDelete}).`);
      showAlert(displayError, 'error');
    } finally {
       setActionLoading(false);
    }
  };

  // Dialog Openers
  const openEditDialog = (material) => {
    if (!material || typeof material.material_id === 'undefined') return;
    setEditMaterial(material);
    setEditFormData({
      material_name: material.material_name || '',
      additional_notes: material.additional_notes || '',
    });
    setEditDialogOpen(true);
  };

  const openDeleteDialog = (material) => {
     if (!material || typeof material.material_id === 'undefined') return;
     setMaterialToDelete(material);
     setDeleteDialogOpen(true);
  };

  // Helper to get icon based on data_type (extension string)
  const getFileIcon = (extension) => {
    const extLower = extension?.toLowerCase() ?? '';
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
      <Paper elevation={1} sx={{ p: { xs: 1.5, sm: 2, md: 3 }, mb: 4 }}>
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
            <Grid item xs={12} sm={6} md={4} lg={3} key={material.material_id}> {/* Use ID from backend */}
              <MaterialCard variant="outlined">
                <MaterialCardContent>
                  <FileIconWrapper> {getFileIcon(material.data?.data_type)} </FileIconWrapper>
                  <Tooltip title={material.material_name || '(No Name)'}>
                      <Typography variant="h6" component="h2" align="center" noWrap gutterBottom> {material.material_name || '(No Name)'} </Typography>
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
                   {/* Link to the actual URL provided by the backend */}
                  <Button size="small" component={MuiLink} href={material.data?.url || '#'} target="_blank" rel="noopener noreferrer" disabled={!material.data?.url || actionLoading}> View </Button>
                  <Box>
                    <Tooltip title="Edit Name/Notes">
                      {/* Ensure Edit button works correctly */}
                      <IconButton size="small" onClick={() => openEditDialog(material)} disabled={actionLoading}> <EditIcon fontSize="small" /> </IconButton>
                    </Tooltip>
                    <Tooltip title="Delete Material">
                       {/* Ensure Delete button works correctly */}
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
        // Ensure materialToDelete and its properties are accessed safely
        description={`Are you sure you want to permanently delete "${materialToDelete?.material_name ?? 'this material'}" (ID: ${materialToDelete?.material_id ?? 'N/A'})? This cannot be undone.`}
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