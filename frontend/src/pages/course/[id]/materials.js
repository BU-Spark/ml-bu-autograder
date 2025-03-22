/**
 * Course Materials Page for BU MET Autograder
 * Handles file uploads, updates, and deletions
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/router';
import {
  Alert,
  Box,
  Button,
  Card,
  CardActions,
  CardContent,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  Grid,
  IconButton,
  LinearProgress,
  Link,
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
  Code as CodeIcon,
  Archive as ZipIcon,
  InsertDriveFile as GenericFileIcon,
  CloudUpload as UploadIcon,
} from '@mui/icons-material';
import { useDropzone } from 'react-dropzone';
import { courseService, materialService } from '../../../services/api';
import CardSkeleton from '../../../components/CardSkeleton';
import ConfirmationDialog from '../../../components/ConfirmationDialog';
import { APP_CONFIG } from '../../../config/config';

// Styled components
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
});

const MaterialCardActions = styled(CardActions)(({ theme }) => ({
  justifyContent: 'space-between',
  borderTop: `1px solid ${theme.palette.divider}`,
}));

const FileIconWrapper = styled(Box)(({ theme }) => ({
  display: 'flex',
  justifyContent: 'center',
  marginBottom: theme.spacing(2),
}));

const DropzoneContainer = styled(Box)(({ theme, isDragActive, isDragAccept, isDragReject }) => ({
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
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
  backgroundColor: isDragActive
    ? theme.palette.action.hover
    : theme.palette.background.default,
  color: theme.palette.text.primary,
  outline: 'none',
  transition: 'border .24s ease-in-out',
  cursor: 'pointer',
}));

const NoMaterialsBox = styled(Box)(({ theme }) => ({
  textAlign: 'center',
  padding: theme.spacing(4),
  backgroundColor: theme.palette.background.paper,
  borderRadius: theme.shape.borderRadius,
  marginTop: theme.spacing(4),
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
  const [uploadFile, setUploadFile] = useState(null);
  const [uploadFormData, setUploadFormData] = useState({
    material_name: '',
    additional_notes: '',
  });

  // State for edit
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editMaterial, setEditMaterial] = useState(null);
  const [editFormData, setEditFormData] = useState({
    material_name: '',
    additional_notes: '',
  });

  // State for delete
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [materialToDelete, setMaterialToDelete] = useState(null);

  // State for alerts
  const [alertOpen, setAlertOpen] = useState(false);
  const [alertMessage, setAlertMessage] = useState('');
  const [alertSeverity, setAlertSeverity] = useState('success');

  // Fetch materials
  useEffect(() => {
    const fetchMaterials = async () => {
      if (!courseId || !semester) return;

      setLoading(true);
      try {
        const materialsData = await materialService.getMaterials(courseId, semester);
        setMaterials(materialsData || []);
        setError(null);
      } catch (err) {
        console.error('Error fetching materials:', err);
        setError(err.message || 'Failed to load course materials');
      } finally {
        setLoading(false);
      }
    };

    fetchMaterials();
  }, [courseId, semester]);

  // File upload handlers
  const onDrop = useCallback((acceptedFiles) => {
    if (acceptedFiles.length === 0) return;

    const file = acceptedFiles[0];

    // Check file size
    if (file.size > APP_CONFIG.maxUploadSize) {
      setAlertMessage(`File size exceeds the maximum limit of ${APP_CONFIG.maxUploadSize / (1024 * 1024)}MB`);
      setAlertSeverity('error');
      setAlertOpen(true);
      return;
    }

    // Check file type
    const fileExtension = `.${file.name.split('.').pop().toLowerCase()}`;
    if (!APP_CONFIG.acceptedFileTypes.materials.includes(fileExtension)) {
      setAlertMessage(`File type not supported. Accepted types: ${APP_CONFIG.acceptedFileTypes.materials.join(', ')}`);
      setAlertSeverity('error');
      setAlertOpen(true);
      return;
    }

    setUploadFile(file);
    setUploadFormData({
      ...uploadFormData,
      material_name: file.name,
    });

    setUploadDialogOpen(true);
  }, [uploadFormData]);

  const { getRootProps, getInputProps, isDragActive, isDragAccept, isDragReject } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/vnd.ms-powerpoint': ['.ppt'],
      'application/vnd.openxmlformats-officedocument.presentationml.presentation': ['.pptx'],
      'text/plain': ['.txt'],
      'application/zip': ['.zip'],
    },
    multiple: false,
  });

  // Handle uploading a material
  const handleUploadMaterial = async () => {
    if (!uploadFile || !uploadFormData.material_name) return;

    setIsUploading(true);
    setUploadProgress(0);

    try {
      // Read file as base64
      const reader = new FileReader();

      reader.onloadstart = () => {
        setUploadProgress(0);
      };

      reader.onprogress = (event) => {
        if (event.lengthComputable) {
          const progress = Math.round((event.loaded / event.total) * 100);
          setUploadProgress(progress);
        }
      };

      reader.onload = async () => {
        const base64Data = reader.result.split(',')[1]; // Remove the data URL prefix

        // Create material data object
        const materialData = {
          course_id: courseId,
          semester: semester,
          material_id: `${Date.now()}-${uploadFile.name.replace(/\s+/g, '-')}`, // Generate a unique ID
          material_name: uploadFormData.material_name,
          additional_notes: uploadFormData.additional_notes || null,
          data: {
            data_type: `.${uploadFile.name.split('.').pop().toLowerCase()}`,
            content: base64Data,
            metadata: {
              size: `${uploadFile.size}`,
              type: uploadFile.type,
              name: uploadFile.name,
            },
          },
        };

        // Upload material
        const result = await materialService.uploadMaterial(materialData);

        // Add to materials list
        setMaterials([...materials, result]);

        // Reset form and close dialog
        setUploadFile(null);
        setUploadFormData({
          material_name: '',
          additional_notes: '',
        });
        setUploadDialogOpen(false);
        setIsUploading(false);

        // Show success alert
        setAlertMessage('Material uploaded successfully');
        setAlertSeverity('success');
        setAlertOpen(true);
      };

      reader.onerror = () => {
        throw new Error('Error reading file');
      };

      reader.readAsDataURL(uploadFile);
    } catch (error) {
      console.error('Error uploading material:', error);
      setAlertMessage(error.message || 'Failed to upload material');
      setAlertSeverity('error');
      setAlertOpen(true);
      setIsUploading(false);
    }
  };

  // Handle updating a material
  const handleUpdateMaterial = async () => {
    if (!editMaterial) return;

    try {
      const updatedMaterial = {
        ...editMaterial,
        material_name: editFormData.material_name,
        additional_notes: editFormData.additional_notes || null,
      };

      await materialService.updateMaterial(updatedMaterial);

      // Update materials list
      const updatedMaterials = materials.map((material) =>
        material.material_id === editMaterial.material_id ? updatedMaterial : material
      );
      setMaterials(updatedMaterials);

      // Reset form and close dialog
      setEditMaterial(null);
      setEditFormData({
        material_name: '',
        additional_notes: '',
      });
      setEditDialogOpen(false);

      // Show success alert
      setAlertMessage('Material updated successfully');
      setAlertSeverity('success');
      setAlertOpen(true);
    } catch (error) {
      console.error('Error updating material:', error);
      setAlertMessage(error.message || 'Failed to update material');
      setAlertSeverity('error');
      setAlertOpen(true);
    }
  };

  // Handle deleting a material
  const handleDeleteMaterial = async () => {
    if (!materialToDelete) return;

    try {
      await materialService.deleteMaterial(
        courseId,
        semester,
        materialToDelete.material_id
      );

      // Remove from materials list
      const updatedMaterials = materials.filter(
        (material) => material.material_id !== materialToDelete.material_id
      );
      setMaterials(updatedMaterials);

      // Close dialog
      setDeleteDialogOpen(false);
      setMaterialToDelete(null);

      // Show success alert
      setAlertMessage('Material deleted successfully');
      setAlertSeverity('success');
      setAlertOpen(true);
    } catch (error) {
      console.error('Error deleting material:', error);
      setAlertMessage(error.message || 'Failed to delete material');
      setAlertSeverity('error');
      setAlertOpen(true);
    }
  };

  // Handle opening edit dialog
  const handleOpenEditDialog = (material) => {
    setEditMaterial(material);
    setEditFormData({
      material_name: material.material_name,
      additional_notes: material.additional_notes || '',
    });
    setEditDialogOpen(true);
  };

  // Handle form input changes
  const handleInputChange = (event, formSetter) => {
    const { name, value } = event.target;
    formSetter((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  // Get file icon based on file type
  const getFileIcon = (fileType) => {
    if (!fileType) return <GenericFileIcon fontSize="large" />;

    switch (fileType.toLowerCase()) {
      case '.pdf':
        return <PdfIcon fontSize="large" color="error" />;
      case '.doc':
      case '.docx':
        return <DocIcon fontSize="large" color="primary" />;
      case '.ppt':
      case '.pptx':
        return <SlideIcon fontSize="large" color="warning" />;
      case '.txt':
        return <FileIcon fontSize="large" color="info" />;
      case '.zip':
        return <ZipIcon fontSize="large" color="action" />;
      default:
        return <GenericFileIcon fontSize="large" />;
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <IconButton
          edge="start"
          aria-label="back to course"
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

      <Paper sx={{ p: 3, mb: 4 }}>
        <Typography variant="h6" gutterBottom>
          Upload New Materials
        </Typography>

        <Typography variant="body2" paragraph>
          Drag and drop files here or click to browse. Supported file types: PDF, DOC, DOCX, PPT, PPTX, TXT, ZIP.
          Maximum file size: {APP_CONFIG.maxUploadSize / (1024 * 1024)}MB.
        </Typography>

        <DropzoneContainer
          {...getRootProps()}
          isDragActive={isDragActive}
          isDragAccept={isDragAccept}
          isDragReject={isDragReject}
        >
          <input {...getInputProps()} />

          <UploadIcon sx={{ fontSize: 48, mb: 2, color: 'action.active' }} />

          {isDragActive ? (
            <Typography variant="body1">Drop the file here...</Typography>
          ) : (
            <Typography variant="body1">
              Drag and drop a file here, or click to select a file
            </Typography>
          )}

          <Button
            variant="contained"
            startIcon={<AttachFileIcon />}
            sx={{ mt: 2 }}
          >
            Browse Files
          </Button>
        </DropzoneContainer>
      </Paper>

      <Typography variant="h5" sx={{ mb: 3 }}>
        All Materials
      </Typography>

      {loading ? (
        <Grid container spacing={3}>
          {[1, 2, 3, 4].map((item) => (
            <Grid item xs={12} sm={6} md={4} lg={3} key={item}>
              <CardSkeleton height={180} />
            </Grid>
          ))}
        </Grid>
      ) : materials.length === 0 ? (
        <NoMaterialsBox>
          <FileIcon sx={{ fontSize: 60, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h6" gutterBottom>
            No Materials Found
          </Typography>
          <Typography variant="body2" color="text.secondary" paragraph>
            You haven't uploaded any course materials yet. Upload your first material to get started.
          </Typography>
          <Button
            variant="contained"
            color="primary"
            startIcon={<UploadIcon />}
            onClick={() => {
              // Trigger the file input click
              document.querySelector('input[type="file"]').click();
            }}
          >
            Upload Material
          </Button>
        </NoMaterialsBox>
      ) : (
        <Grid container spacing={3}>
          {materials.map((material) => (
            <Grid item xs={12} sm={6} md={4} lg={3} key={material.material_id}>
              <MaterialCard>
                <MaterialCardContent>
                  <FileIconWrapper>
                    {getFileIcon(material.data.data_type)}
                  </FileIconWrapper>

                  <Typography variant="h6" component="h2" align="center" noWrap gutterBottom>
                    {material.material_name}
                  </Typography>

                  <Box sx={{ mb: 1 }}>
                    <Chip
                      label={material.data.data_type.replace('.', '').toUpperCase()}
                      size="small"
                      color={
                        material.data.data_type === '.pdf' ? 'error' :
                        material.data.data_type === '.doc' || material.data.data_type === '.docx' ? 'primary' :
                        material.data.data_type === '.ppt' || material.data.data_type === '.pptx' ? 'warning' :
                        'default'
                      }
                      variant="outlined"
                    />
                  </Box>

                  {material.additional_notes && (
                    <Typography
                      variant="body2"
                      color="text.secondary"
                      sx={{
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        display: '-webkit-box',
                        WebkitLineClamp: 2,
                        WebkitBoxOrient: 'vertical',
                        mt: 1,
                      }}
                    >
                      {material.additional_notes}
                    </Typography>
                  )}
                </MaterialCardContent>

                <MaterialCardActions>
                  <Button
                    size="small"
                    component={Link}
                    href={material.data.url || '#'}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    View
                  </Button>

                  <Box>
                    <IconButton
                      size="small"
                      color="primary"
                      onClick={() => handleOpenEditDialog(material)}
                    >
                      <EditIcon fontSize="small" />
                    </IconButton>

                    <IconButton
                      size="small"
                      color="error"
                      onClick={() => {
                        setMaterialToDelete(material);
                        setDeleteDialogOpen(true);
                      }}
                    >
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </Box>
                </MaterialCardActions>
              </MaterialCard>
            </Grid>
          ))}
        </Grid>
      )}

      {/* Upload Material Dialog */}
      <Dialog
        open={uploadDialogOpen}
        onClose={() => !isUploading && setUploadDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Upload Material</DialogTitle>
        <DialogContent>
          {isUploading && (
            <Box sx={{ width: '100%', mb: 2 }}>
              <LinearProgress variant="determinate" value={uploadProgress} />
              <Typography variant="body2" color="text.secondary" align="center" sx={{ mt: 1 }}>
                {uploadProgress}% Uploaded
              </Typography>
            </Box>
          )}

          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            {getFileIcon(`.${uploadFile?.name.split('.').pop().toLowerCase()}`)}
            <Typography variant="body1" sx={{ ml: 1 }}>
              {uploadFile?.name}
            </Typography>
          </Box>

          <TextField
            name="material_name"
            label="Material Name"
            fullWidth
            value={uploadFormData.material_name}
            onChange={(e) => handleInputChange(e, setUploadFormData)}
            margin="normal"
            required
            disabled={isUploading}
          />

          <TextField
            name="additional_notes"
            label="Additional Notes"
            fullWidth
            multiline
            rows={3}
            value={uploadFormData.additional_notes}
            onChange={(e) => handleInputChange(e, setUploadFormData)}
            margin="normal"
            disabled={isUploading}
            helperText="Optional notes about this material"
          />
        </DialogContent>

        <DialogActions>
          <Button
            onClick={() => setUploadDialogOpen(false)}
            disabled={isUploading}
          >
            Cancel
          </Button>
          <Button
            onClick={handleUploadMaterial}
            variant="contained"
            color="primary"
            disabled={!uploadFormData.material_name || isUploading}
            startIcon={<UploadIcon />}
          >
            {isUploading ? 'Uploading...' : 'Upload'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Edit Material Dialog */}
      <Dialog
        open={editDialogOpen}
        onClose={() => setEditDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Edit Material</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            {getFileIcon(editMaterial?.data.data_type)}
            <Typography variant="body2" color="text.secondary" sx={{ ml: 1 }}>
              {editMaterial?.data.data_type}
            </Typography>
          </Box>

          <TextField
            name="material_name"
            label="Material Name"
            fullWidth
            value={editFormData.material_name}
            onChange={(e) => handleInputChange(e, setEditFormData)}
            margin="normal"
            required
          />

          <TextField
            name="additional_notes"
            label="Additional Notes"
            fullWidth
            multiline
            rows={3}
            value={editFormData.additional_notes}
            onChange={(e) => handleInputChange(e, setEditFormData)}
            margin="normal"
            helperText="Optional notes about this material"
          />
        </DialogContent>

        <DialogActions>
          <Button onClick={() => setEditDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleUpdateMaterial}
            variant="contained"
            color="primary"
            disabled={!editFormData.material_name}
          >
            Update
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Material Confirmation Dialog */}
      <ConfirmationDialog
        open={deleteDialogOpen}
        title="Delete Material"
        message={`Are you sure you want to delete "${materialToDelete?.material_name}"? This action cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        confirmButtonProps={{ color: 'error' }}
        onConfirm={handleDeleteMaterial}
        onCancel={() => {
          setDeleteDialogOpen(false);
          setMaterialToDelete(null);
        }}
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