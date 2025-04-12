/**
 * Course Materials Page for BU MET Autograder
 * Handles file uploads, updates, and deletions
 */

import React, { useState, useEffect, useCallback } from 'react'; // Added useCallback
import { useRouter } from 'next/router';
import {
  Alert,
  Box,
  Button,
  Card,
  CardActions,
  CardContent,
  Chip,
  CircularProgress, // Added
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  Grid,
  IconButton,
  LinearProgress,
  Link, // Keep Link for viewing
  Paper,
  Snackbar,
  TextField,
  Typography,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import {
  ArrowBack as ArrowBackIcon,
  AttachFile as AttachFileIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  FilePresent as FileIcon,
  PictureAsPdf as PdfIcon,
  Description as DocIcon,
  Slideshow as SlideIcon,
  // Code as CodeIcon, // Not used in getFileIcon
  // Archive as ZipIcon, // Added specific icon
  FolderZip as ZipIcon, // Use FolderZip
  InsertDriveFile as GenericFileIcon,
  CloudUpload as UploadIcon,
} from '@mui/icons-material';
import { useDropzone } from 'react-dropzone';
// Assuming api.js is correctly imported
import { courseService, materialService } from '../../../api';
import CardSkeleton from '../../../components/CardSkeleton'; // Assuming this exists
import ConfirmationDialog from '../../../components/ConfirmationDialog'; // Assuming this exists
// Assuming config.js provides APP_CONFIG
import { APP_CONFIG } from '../../../config';

// Styled components (Keep as they are)
const MaterialCard = styled(Card)(({ theme }) => ({
  height: '100%',
  display: 'flex',
  flexDirection: 'column',
  transition: 'transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out',
  '&:hover': {
    transform: 'translateY(-4px)',
    boxShadow: theme.shadows[6],
  },
}));

const MaterialCardContent = styled(CardContent)({
  flexGrow: 1,
  display: 'flex',        // Added
  flexDirection: 'column', // Added
  alignItems: 'center',   // Added - Center content like icon/title
});

const MaterialCardActions = styled(CardActions)(({ theme }) => ({
  justifyContent: 'space-between',
  borderTop: `1px solid ${theme.palette.divider}`,
  padding: theme.spacing(1), // Reduce padding slightly
}));

const FileIconWrapper = styled(Box)(({ theme }) => ({
  display: 'flex',
  justifyContent: 'center',
  marginBottom: theme.spacing(2),
  fontSize: '3rem', // Increase icon size
}));

const DropzoneContainer = styled(Box)(({ theme, isDragActive, isDragAccept, isDragReject }) => ({
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  textAlign: 'center', // Center text
  padding: theme.spacing(4),
  borderWidth: 2,
  borderRadius: theme.shape.borderRadius,
  borderColor: isDragAccept
    ? theme.palette.success.main
    : isDragReject
    ? theme.palette.error.main
    : isDragActive
    ? theme.palette.primary.main
    : theme.palette.divider,
  borderStyle: 'dashed',
  backgroundColor: isDragAccept
    ? theme.palette.success.lighter // Use lighter backgrounds on accept/reject
    : isDragReject
    ? theme.palette.error.lighter
    : isDragActive
    ? theme.palette.action.hover
    : theme.palette.background.default,
  color: theme.palette.text.secondary, // Use secondary color
  outline: 'none',
  transition: 'border .24s ease-in-out, background-color .24s ease-in-out', // Add background transition
  cursor: 'pointer',
  minHeight: '150px', // Ensure dropzone has some height
}));

const NoMaterialsBox = styled(Box)(({ theme }) => ({
  textAlign: 'center',
  padding: theme.spacing(4),
  backgroundColor: theme.palette.background.default, // Use default background
  borderRadius: theme.shape.borderRadius,
  marginTop: theme.spacing(4),
  border: `1px dashed ${theme.palette.divider}`,
}));

// Main component
export default function CourseMaterials() {
  const router = useRouter();
  const { id: courseId, semester } = router.query;

  // State for materials
  const [materials, setMaterials] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // State for upload
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadFile, setUploadFile] = useState(null); // Holds the File object
  const [uploadFormData, setUploadFormData] = useState({
    material_name: '',
    additional_notes: '',
  });

  // State for edit
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editMaterial, setEditMaterial] = useState(null); // Holds the material object being edited
  const [editFormData, setEditFormData] = useState({
    material_name: '',
    additional_notes: '',
  });

  // State for delete
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [materialToDelete, setMaterialToDelete] = useState(null); // Holds the material object to delete

  // State for alerts
  const [alertOpen, setAlertOpen] = useState(false);
  const [alertMessage, setAlertMessage] = useState('');
  const [alertSeverity, setAlertSeverity] = useState('success');

  // --- Helper Functions ---
  const showAlert = useCallback((message, severity = 'success') => {
    setAlertMessage(message);
    setAlertSeverity(severity);
    setAlertOpen(true);
  }, []);

  const handleInputChange = useCallback((event, formSetter) => {
    const { name, value } = event.target;
    formSetter((prev) => ({
      ...prev,
      [name]: value,
    }));
  }, []);

  // --- Data Fetching ---
  const fetchMaterials = useCallback(async () => {
      if (!courseId || !semester) return;
      setLoading(true);
      setError(null);
      try {
        // Use the correct service call as defined in api.js
        const materialsData = await materialService.getMaterials(semester, courseId); // Correct order: semester, courseId
        setMaterials(materialsData || []);
      } catch (err) {
        console.error('Error fetching materials:', err);
        const errorMsg = err.message || 'Failed to load course materials';
        setError(errorMsg);
        showAlert(errorMsg, 'error');
      } finally {
        setLoading(false);
      }
  }, [courseId, semester, showAlert]); // Dependencies

  useEffect(() => {
    fetchMaterials();
  }, [fetchMaterials]); // Fetch when function reference is stable


  // --- File Upload ---
  const onDrop = useCallback((acceptedFiles) => {
    if (acceptedFiles.length === 0) {
        showAlert('No valid files were dropped.', 'warning');
        return;
    }

    const file = acceptedFiles[0];

    // Check file size
    if (file.size > APP_CONFIG.maxUploadSize) {
      showAlert(`File size exceeds the maximum limit of ${APP_CONFIG.maxUploadSize / (1024 * 1024)}MB`, 'error');
      return;
    }

    // Check file type based on extension
    const fileExtension = file.name.split('.').pop()?.toLowerCase();
    // Prepend dot for comparison if extension exists
    const fileTypeWithDot = fileExtension ? `.${fileExtension}` : '';

    if (!fileTypeWithDot || !APP_CONFIG.acceptedFileTypes.materials.includes(fileTypeWithDot)) {
        showAlert(`File type "${fileExtension || 'unknown'}" not supported. Accepted types: ${APP_CONFIG.acceptedFileTypes.materials.join(', ')}`, 'error');
        return;
    }


    setUploadFile(file);
    // Default material name to file name without extension
    const fileNameWithoutExt = file.name.substring(0, file.name.lastIndexOf('.')) || file.name;
    setUploadFormData({
      material_name: fileNameWithoutExt,
      additional_notes: '', // Reset notes
    });

    setUploadDialogOpen(true); // Open dialog after successful drop and validation
  }, [showAlert]); // Dependency

  // Configure Dropzone
  const { getRootProps, getInputProps, isDragActive, isDragAccept, isDragReject } = useDropzone({
    onDrop,
    accept: APP_CONFIG.acceptedFileTypes.materials.reduce((acc, ext) => {
        // Attempt to map extension to MIME type for stricter browser filtering
        // This is best-effort and might not cover all cases/browsers perfectly
        switch(ext) {
            case '.pdf': acc['application/pdf'] = [ext]; break;
            case '.doc': acc['application/msword'] = [ext]; break;
            case '.docx': acc['application/vnd.openxmlformats-officedocument.wordprocessingml.document'] = [ext]; break;
            case '.ppt': acc['application/vnd.ms-powerpoint'] = [ext]; break;
            case '.pptx': acc['application/vnd.openxmlformats-officedocument.presentationml.presentation'] = [ext]; break;
            case '.txt': acc['text/plain'] = [ext]; break;
            case '.zip': acc['application/zip'] = [ext]; break;
            // Add other types if needed
            default: console.warn(`No specific MIME type mapped for ${ext}`); break; // Fallback?
        }
        return acc;
    }, {}),
    multiple: false,
    noClick: true, // Prevent opening file dialog on container click if button exists
    noKeyboard: true, // Disable keyboard interaction if preferred
  });


  // --- CRUD Handlers ---

  // Handle uploading a material
  const handleUploadMaterial = async () => {
    if (!uploadFile || !uploadFormData.material_name?.trim()) {
        showAlert('File and Material Name are required.', 'warning');
        return;
    }

    setIsUploading(true);
    setUploadProgress(0);

    // Function to read file and return promise
    const readFileAsBase64 = (file) => {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onloadstart = () => setUploadProgress(0);
            reader.onprogress = (event) => {
                if (event.lengthComputable) {
                  setUploadProgress(Math.round((event.loaded / event.total) * 100));
                }
            };
            reader.onload = () => resolve(reader.result.split(',')[1]); // Resolve with base64 string
            reader.onerror = (error) => reject(error);
            reader.readAsDataURL(file);
        });
    };

    try {
        const base64Data = await readFileAsBase64(uploadFile);
        const fileExtension = uploadFile.name.split('.').pop()?.toLowerCase() ?? '';

        // Generate a somewhat unique ID (backend might override this)
        // Consider using UUID library for truly unique IDs if needed client-side
        const generatedMaterialId = `${Date.now()}-${uploadFile.name.replace(/[^a-zA-Z0-9.-]/g, '-')}`;

        const materialPayload = {
            // Ensure payload matches the CourseMaterial Pydantic model
            course_id: courseId,
            semester: semester,
            material_id: generatedMaterialId, // Backend might ignore/replace this ID
            material_name: uploadFormData.material_name.trim(),
            additional_notes: uploadFormData.additional_notes?.trim() || null, // Send null if empty/whitespace
            data: { // Nested data object
                // Use the correct enum value if DataType enum is available, otherwise string
                data_type: fileExtension, // Just the extension string as per model example
                content: base64Data,
                metadata: { // Optional metadata
                    size: String(uploadFile.size), // Ensure string
                    type: uploadFile.type || 'application/octet-stream', // Fallback type
                    name: uploadFile.name,
                },
            },
        };

        // Call the correct service function
        const uploadedMaterial = await materialService.uploadMaterial(materialPayload);

        // Add the material returned *from the server* (it might have a different ID)
        setMaterials(prev => [...prev, uploadedMaterial]);

        showAlert('Material uploaded successfully');
        setUploadDialogOpen(false);
        setUploadFile(null);
        setUploadFormData({ material_name: '', additional_notes: '' });

    } catch (error) {
        console.error('Error uploading material:', error);
        showAlert(error.message || 'Failed to upload material', 'error');
    } finally {
        setIsUploading(false);
        setUploadProgress(0);
    }
  };


  // Handle updating a material's metadata (name, notes)
  const handleUpdateMaterial = async () => {
    if (!editMaterial || !editFormData.material_name?.trim()) {
        showAlert('Material Name cannot be empty.', 'warning');
        return;
    }

     // Prepare only the fields allowed for update (name, notes)
     // Assuming the PATCH endpoint can handle partial updates for these fields
     // NOTE: The current backend PATCH expects the *full* CourseMaterial object.
     // This means we *must* send the potentially large 'data' field back.
     // Ideally, the backend would have a different PATCH endpoint for metadata only.

    const updatedMaterialPayload = {
        ...editMaterial, // Start with existing data
        material_name: editFormData.material_name.trim(),
        additional_notes: editFormData.additional_notes?.trim() || null,
        // data field remains unchanged but is required by the current backend PATCH
    };

    // Prevent update if nothing changed
    if (updatedMaterialPayload.material_name === editMaterial.material_name &&
        updatedMaterialPayload.additional_notes === editMaterial.additional_notes) {
        setEditDialogOpen(false);
        return;
    }

    setIsUploading(true); // Use same flag for generic action loading
    try {
      // Call the correct service function
      const updatedMaterialFromServer = await materialService.updateMaterial(updatedMaterialPayload);

      // Update state with the data returned from the server
      setMaterials(prev => prev.map(m =>
        m.material_id === editMaterial.material_id ? updatedMaterialFromServer : m
      ));

      showAlert('Material updated successfully');
      setEditDialogOpen(false);
      setEditMaterial(null);

    } catch (error) {
      console.error('Error updating material:', error);
      showAlert(error.message || 'Failed to update material', 'error');
    } finally {
        setIsUploading(false);
    }
  };

  // Handle deleting a material
  const handleDeleteMaterial = async () => {
    if (!materialToDelete || !semester || !courseId) return;

    setIsUploading(true); // Use loading flag
    try {
      // <<< --- CORRECTED Argument Order --- >>>
      await materialService.deleteMaterial(
        semester, // Arg 1: semester
        courseId, // Arg 2: courseId
        materialToDelete.material_id // Arg 3: materialId
      );

      setMaterials(prev => prev.filter(
        (m) => m.material_id !== materialToDelete.material_id
      ));

      showAlert('Material deleted successfully');

    } catch (error) {
      console.error('Error deleting material:', error);
      showAlert(error.message || 'Failed to delete material', 'error');
    } finally {
       setDeleteDialogOpen(false);
       setMaterialToDelete(null);
       setIsUploading(false);
    }
  };

  // Handle opening edit dialog
  const openEditDialog = (material) => {
    setEditMaterial(material);
    setEditFormData({
      material_name: material.material_name || '',
      additional_notes: material.additional_notes || '',
    });
    setEditDialogOpen(true);
  };

  // Handle opening delete confirmation
  const openDeleteDialog = (material) => {
    setMaterialToDelete(material);
    setDeleteDialogOpen(true);
  };

  // Get file icon based on file extension string (e.g., "pdf", "docx")
  const getFileIcon = (extension) => {
    const extLower = extension?.toLowerCase().replace('.', '') ?? ''; // Ensure lowercase, remove dot

    switch (extLower) {
      case 'pdf': return <PdfIcon fontSize="inherit" color="error" />;
      case 'doc': case 'docx': return <DocIcon fontSize="inherit" color="primary" />;
      case 'ppt': case 'pptx': return <SlideIcon fontSize="inherit" color="warning" />;
      case 'txt': return <FileIcon fontSize="inherit" color="info" />;
      case 'zip': return <ZipIcon fontSize="inherit" color="action" />;
      // Add more specific icons if needed
      default: return <GenericFileIcon fontSize="inherit" />;
    }
  };


  // --- Main Render ---
  return (
    <Box sx={{ p: { xs: 1, sm: 2, md: 3 } }}>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <IconButton
          edge="start"
          aria-label="back to course"
          title="Back to Course Overview"
          onClick={() => router.push(`/course/${courseId}?semester=${semester}`)}
          sx={{ mr: 1 }}
        >
          <ArrowBackIcon />
        </IconButton>
        <Typography variant="h4" component="h1">
          Course Materials
        </Typography>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* Upload Section */}
      <Paper sx={{ p: 3, mb: 4 }}>
        <Typography variant="h6" gutterBottom>
          Upload New Material
        </Typography>
        <Typography variant="body2" color="text.secondary" paragraph>
          Drag & drop or click below. Max size: {APP_CONFIG.maxUploadSize / (1024 * 1024)}MB.
          Accepted: {APP_CONFIG.acceptedFileTypes.materials.join(', ')}.
        </Typography>
        <DropzoneContainer
          {...getRootProps()}
          isDragActive={isDragActive}
          isDragAccept={isDragAccept}
          isDragReject={isDragReject}
        >
          <input {...getInputProps()} />
          <UploadIcon sx={{ fontSize: 40, mb: 1 }} />
          {isDragAccept && <Typography>Drop file here!</Typography>}
          {isDragReject && <Typography color="error">File type not accepted.</Typography>}
          {!isDragActive && <Typography>Drag & drop file or click to browse</Typography>}
        </DropzoneContainer>
      </Paper>

      {/* Materials List Section */}
      <Typography variant="h5" sx={{ mb: 3 }}>
        Uploaded Materials
      </Typography>
      {loading ? (
        <Grid container spacing={3}>
          {[1, 2, 3, 4].map((item) => (
            <Grid item xs={12} sm={6} md={4} lg={3} key={item}>
              <CardSkeleton height={220} /> {/* Adjusted height */}
            </Grid>
          ))}
        </Grid>
      ) : materials.length === 0 ? (
        <NoMaterialsBox>
          <FileIcon sx={{ fontSize: 60, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h6" gutterBottom>No Materials Found</Typography>
          <Typography color="text.secondary">Upload materials using the section above.</Typography>
        </NoMaterialsBox>
      ) : (
        <Grid container spacing={3}>
          {materials.map((material) => (
            <Grid item xs={12} sm={6} md={4} lg={3} key={material.material_id}>
              <MaterialCard variant="outlined">
                <MaterialCardContent>
                  <FileIconWrapper>
                    {getFileIcon(material.data?.data_type)}
                  </FileIconWrapper>
                  <Tooltip title={material.material_name}>
                    <Typography variant="h6" component="h2" align="center" noWrap gutterBottom>
                        {material.material_name}
                    </Typography>
                  </Tooltip>
                  <Chip
                     label={(material.data?.data_type || 'unknown').replace('.', '').toUpperCase()}
                     size="small"
                     variant="outlined"
                     sx={{ mb: 1 }}
                   />
                   {material.additional_notes && (
                      <Tooltip title={material.additional_notes}>
                         <Typography
                           variant="body2"
                           color="text.secondary"
                           align="center"
                           sx={{
                             mt: 1, height: '40px', // Fixed height for 2 lines
                             overflow: 'hidden', textOverflow: 'ellipsis',
                             display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical',
                           }}
                         >
                          {material.additional_notes}
                        </Typography>
                      </Tooltip>
                   )}
                </MaterialCardContent>
                <MaterialCardActions>
                   {/* Assume data.url might exist if it's a reference, otherwise disable/hide */}
                  <Button
                    size="small"
                    component={Link}
                    href={material.data?.url || '#'} // Use optional chaining
                    target="_blank"
                    rel="noopener noreferrer"
                    disabled={!material.data?.url} // Disable if no URL
                  >
                    View
                  </Button>
                  <Box>
                    <Tooltip title="Edit Metadata">
                      <IconButton size="small" onClick={() => openEditDialog(material)}>
                        <EditIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Delete Material">
                      <IconButton size="small" color="error" onClick={() => openDeleteDialog(material)}>
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </Box>
                </MaterialCardActions>
              </MaterialCard>
            </Grid>
          ))}
        </Grid>
      )}

      {/* --- DIALOGS --- */}

      {/* Upload Material Dialog */}
      <Dialog open={uploadDialogOpen} onClose={() => !isUploading && setUploadDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Upload New Material</DialogTitle>
        <DialogContent>
          {uploadFile && (
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, p:1, bgcolor: 'action.hover', borderRadius: 1 }}>
              <Box sx={{ mr: 1.5, fontSize: '1.5rem' }}>{getFileIcon(uploadFile.name.split('.').pop())}</Box>
              <Box>
                  <Typography variant="body1" fontWeight="medium">{uploadFile.name}</Typography>
                  <Typography variant="caption" color="text.secondary">{(uploadFile.size / 1024).toFixed(1)} KB</Typography>
              </Box>
            </Box>
          )}
          {isUploading && (
            <Box sx={{ width: '100%', my: 2 }}>
              <LinearProgress variant="determinate" value={uploadProgress} />
              <Typography variant="caption" display="block" textAlign="center" sx={{ mt: 0.5 }}>
                Uploading: {uploadProgress}%
              </Typography>
            </Box>
          )}
          <TextField
            autoFocus
            name="material_name"
            label="Material Name"
            fullWidth
            value={uploadFormData.material_name}
            onChange={(e) => handleInputChange(e, setUploadFormData)}
            margin="dense"
            required
            disabled={isUploading}
            error={!uploadFormData.material_name?.trim()}
            helperText={!uploadFormData.material_name?.trim() ? 'Name is required' : ''}
          />
          <TextField
            name="additional_notes"
            label="Additional Notes (Optional)"
            fullWidth
            multiline
            rows={3}
            value={uploadFormData.additional_notes}
            onChange={(e) => handleInputChange(e, setUploadFormData)}
            margin="dense"
            disabled={isUploading}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setUploadDialogOpen(false)} disabled={isUploading}>Cancel</Button>
          <Button
            onClick={handleUploadMaterial}
            variant="contained"
            color="primary"
            disabled={!uploadFormData.material_name?.trim() || isUploading}
            startIcon={isUploading ? <CircularProgress size={20} color="inherit"/> : <UploadIcon />}
          >
            {isUploading ? 'Uploading...' : 'Confirm Upload'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Edit Material Dialog */}
      <Dialog open={editDialogOpen} onClose={() => setEditDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Edit Material Metadata</DialogTitle>
        <DialogContent>
          {editMaterial && (
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, p:1, bgcolor: 'action.hover', borderRadius: 1 }}>
               <Box sx={{ mr: 1.5, fontSize: '1.5rem' }}>{getFileIcon(editMaterial.data?.data_type)}</Box>
               <Typography variant="body1" fontWeight="medium">{editMaterial.material_name} ({editMaterial.data?.data_type})</Typography>
            </Box>
           )}
          <TextField
            autoFocus
            name="material_name"
            label="Material Name"
            fullWidth
            value={editFormData.material_name}
            onChange={(e) => handleInputChange(e, setEditFormData)}
            margin="dense"
            required
             error={!editFormData.material_name?.trim()}
            helperText={!editFormData.material_name?.trim() ? 'Name is required' : ''}
          />
          <TextField
            name="additional_notes"
            label="Additional Notes (Optional)"
            fullWidth
            multiline
            rows={3}
            value={editFormData.additional_notes}
            onChange={(e) => handleInputChange(e, setEditFormData)}
            margin="dense"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditDialogOpen(false)} disabled={isUploading}>Cancel</Button>
          <Button
            onClick={handleUpdateMaterial}
            variant="contained"
            color="primary"
            disabled={!editFormData.material_name?.trim() || isUploading}
            startIcon={isUploading ? <CircularProgress size={20} color="inherit"/> : <EditIcon />}
          >
            {isUploading ? 'Saving...' : 'Save Changes'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Material Confirmation Dialog */}
      <ConfirmationDialog
        open={deleteDialogOpen}
        onClose={() => setDeleteDialogOpen(false)} // Use onClose
        title="Delete Material"
        description={`Are you sure you want to delete the material "${materialToDelete?.material_name}"? This action cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        confirmColor="error" // Use string 'error'
        onConfirm={handleDeleteMaterial}
        loading={isUploading} // Use loading flag
      />

      {/* Alert Snackbar */}
      <Snackbar
        open={alertOpen}
        autoHideDuration={6000}
        onClose={() => setAlertOpen(false)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          onClose={() => setAlertOpen(false)}
          severity={alertSeverity}
          variant="filled"
          sx={{ width: '100%' }}
        >
          {alertMessage}
        </Alert>
      </Snackbar>
    </Box>
  );
}