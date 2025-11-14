import React, { useState, useRef, useEffect } from 'react';
import { Upload, FileText, Shield, X, CheckCircle, AlertCircle, Loader2, Download, Trash2, RefreshCw } from 'lucide-react';
import config from '../../Config';
import { useToast } from './ToastProvider';

const ConfirmationDialog = ({ isOpen, onClose, onConfirm, title, message, type = 'danger' }) => {
    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[60] p-4">
            <div className="bg-white rounded-lg shadow-xl p-6 max-w-md w-full">
                <h3 className="text-lg font-semibold text-gray-900 mb-2">{title}</h3>
                <p className="text-sm text-gray-600 mb-6">{message}</p>
                <div className="flex space-x-3 justify-end">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 transition-colors"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={onConfirm}
                        className={`px-4 py-2 rounded-md text-white transition-colors ${type === 'danger'
                            ? 'bg-red-600 hover:bg-red-700'
                            : 'bg-blue-600 hover:bg-blue-700'
                            }`}
                    >
                        Confirm
                    </button>
                </div>
            </div>
        </div>
    );
};

const KYCDocumentUploadPage = ({
    isOpen = true,
    onClose = () => { },
    user = { idnumber: '12345678', id: '1' },
    onSubmitSuccess
}) => {
    const [kraPin, setKraPin] = useState('');
    const [taxPayerName, setTaxPayerName] = useState('');
    const [email, setEmail] = useState('');
    const [policeClearance, setPoliceClearance] = useState('');
    const [clearedUserName, setClearedUserName] = useState('');
    const [idNumber, setIdNumber] = useState(user?.idnumber || '');
    const [loading, setLoading] = useState(false);
    const [errors, setErrors] = useState({});
    const { showToast } = useToast();

    // Document status with document IDs for backend operations
    const [documentStatus, setDocumentStatus] = useState({
        kra: { uploaded: false, fileName: '', fileUrl: '', documentId: null },
        police: { uploaded: false, fileName: '', fileUrl: '', documentId: null }
    });

    const [confirmDialog, setConfirmDialog] = useState({
        isOpen: false,
        title: '',
        message: '',
        onConfirm: () => { },
        type: 'danger'
    });

    const kraPinFileRef = useRef(null);
    const policeClearanceFileRef = useRef(null);
    const genericFileRef = useRef(null);

    // Check for existing documents when modal opens
    useEffect(() => {

        if (isOpen && user?.id) {
            checkExistingDocuments();
        }
    }, [isOpen, user?.id]);

    // Validate name match
    useEffect(() => {
        if (taxPayerName && clearedUserName) {

            if (taxPayerName !== clearedUserName) {
                showToast('The taxpayer name does not match police clearance form details', 'error');
                setErrors(prev => ({ ...prev, nameMatch: 'The taxpayer name does not match police clearance form details' }));
            } else {
                setErrors(prev => ({ ...prev, nameMatch: '' }));
            }
        }
    }, [taxPayerName, clearedUserName]);

    const checkExistingDocuments = async () => {
        try {
            // Check KRA PIN document
            const kraResponse = await fetch(
                `${config.API_URL}/document/status/${user.id}/kra_pin`
            );
            const kraData = await kraResponse.json();

            if (kraData.exists) {

                setKraPin(kraData.document.extracted_data["PIN"] || '');
                setTaxPayerName(kraData.document.extracted_data["Taxpayer Name"] || '');
                setEmail(kraData.document.extracted_data["Email address"] || '');
                setDocumentStatus(prev => ({
                    ...prev,
                    kra: {
                        uploaded: true,
                        fileName: kraData.document.filename,
                        fileUrl: kraData.document.gcp_url,
                        documentId: kraData.document.id
                    }
                }));
                setErrors(prev => ({ ...prev, nameMatch: '' }));
            }

            // Check Police Clearance document
            const policeResponse = await fetch(
                `${config.API_URL}/document/status/${user.id}/police_clearance`
            );
            const policeData = await policeResponse.json();

            if (policeData.exists) {

                setPoliceClearance(policeData.document.extracted_data["Reference Number"] || '');
                setClearedUserName(policeData.document.extracted_data["Name"] || '');
                setIdNumber(policeData.document.extracted_data["ID Number"] || '');
                setDocumentStatus(prev => ({
                    ...prev,
                    police: {
                        uploaded: true,
                        fileName: policeData.document.filename,
                        fileUrl: policeData.document.gcp_url,
                        documentId: policeData.document.id
                    }
                }));
                setErrors(prev => ({ ...prev, nameMatch: '' }));
            }
        } catch (err) {
            console.error('Error checking existing documents:', err);
        }
    };

    const uploadFile = async (endpoint, file, docType) => {
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file);
        formData.append('agent_id', user?.id || '');
        setLoading(true);

        try {
            const res = await fetch(`${config.API_URL}/document${endpoint}`, {
                method: 'POST',
                body: formData
            });

            const result = await res.json();

            if (!res.ok || result.error) {
                showToast(result.error || 'Upload failed', 'error');
                return;
            }

            // Handle KRA PIN response
            if (docType === 'kra') {
                setKraPin(result.kraPin || '');
                setTaxPayerName(result.taxPayerName || '');
                setEmail(result.email || '');

                setDocumentStatus(prev => ({
                    ...prev,
                    kra: {
                        uploaded: true,
                        fileName: file.name,
                        fileUrl: result.gcp_url,
                        documentId: null // Backend doesn't return ID in extract response
                    }
                }));
                setErrors(prev => ({ ...prev, nameMatch: '' }));
            }

            // Handle Police Clearance response
            if (docType === 'police') {
                // Validate ID number match
                if (result.idNo && idNumber && result.idNo !== idNumber) {
                    showToast('The ID number does not match police clearance form details', 'error');
                    setErrors(prev => ({
                        ...prev,
                        nameMatch: 'The ID number does not match police clearance form details'
                    }));
                    resetPoliceClearance();
                    return;
                }

                setPoliceClearance(result.refNo || '');
                setClearedUserName(result.name || '');
                if (result.idNo) setIdNumber(result.idNo);

                setDocumentStatus(prev => ({
                    ...prev,
                    police: {
                        uploaded: true,
                        fileName: file.name,
                        fileUrl: result.gcp_url,
                        documentId: null
                    }
                }));

                setErrors(prev => ({ ...prev, nameMatch: '' }));
            }

            showToast(
                `${docType === 'kra' ? 'KRA PIN' : 'Police Clearance'} document uploaded successfully`,
                'success'
            );

        } catch (err) {
            console.error('Upload failed:', err);
            showToast('File upload failed.', 'error');
        } finally {
            setLoading(false);
        }
    };

    const handleDownload = async (docType) => {
        const doc = documentStatus[docType];

        if (!doc.uploaded) {
            showToast('No document to download', 'error');
            return;
        }

        try {
            // If we have a document ID, use the download endpoint
            if (doc.documentId) {
                const response = await fetch(
                    `${config.API_URL}/document/download/${doc.documentId}?inline=false`
                );

                if (!response.ok) {
                    throw new Error('Download failed');
                }

                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = url;
                link.download = doc.fileName;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                window.URL.revokeObjectURL(url);

                showToast(`Downloading ${doc.fileName}`, 'success');
            } else if (doc.fileUrl) {
                // Fallback: open the GCP URL
                window.open(doc.fileUrl, '_blank');
                showToast(`Opening ${doc.fileName}`, 'success');
            }
        } catch (err) {
            console.error('Download error:', err);
            showToast('Download failed', 'error');
        }
    };

    const handleDelete = async (docType) => {
        const doc = documentStatus[docType];

        setConfirmDialog({
            isOpen: true,
            title: 'Delete Document',
            message: `Are you sure you want to delete this ${docType === 'kra' ? 'KRA PIN' : 'Police Clearance'
                } document? This action cannot be undone.`,
            type: 'danger',
            onConfirm: async () => {
                setConfirmDialog(prev => ({ ...prev, isOpen: false }));
                setLoading(true);

                try {
                    // If we have a document ID, call the delete endpoint
                    if (doc.documentId) {
                        const response = await fetch(
                            `${config.API_URL}/document/delete/${doc.documentId}`,
                            { method: 'DELETE' }
                        );

                        if (!response.ok) {
                            throw new Error('Delete failed');
                        }
                    }

                    // Clear state
                    if (docType === 'kra') {
                        setKraPin('');
                        setTaxPayerName('');
                        setEmail('');
                        resetFileInput(kraPinFileRef);
                    } else if (docType === 'police') {
                        resetPoliceClearance();
                    }

                    setDocumentStatus(prev => ({
                        ...prev,
                        [docType]: { uploaded: false, fileName: '', fileUrl: '', documentId: null }
                    }));
                    setLoading(false);

                    showToast('Document deleted successfully', 'success');
                } catch (err) {
                    console.error('Delete error:', err);
                    setLoading(false);
                    showToast('Delete failed', 'error');
                }
            }
        });
    };

    const handleReupload = async (docType) => {
        console.log("The docType is >>", docType)
        setConfirmDialog({
            isOpen: true,
            title: 'Re-upload Document',
            message: `Are you sure you want to replace the existing ${docType === 'kra' ? 'KRA PIN' : 'Police Clearance'
                } document?`,
            type: 'warning',
            onConfirm: async () => {
                // fileRef.current?.click();
                setConfirmDialog(prev => ({ ...prev, isOpen: false }));

                // Create a promise to wait for file selection
                const file = await new Promise((resolve) => {
                    const input = genericFileRef.current;

                    // Create a one-time event listener for file selection
                    const handleFileSelect = (e) => {
                        const selectedFile = e.target.files[0];
                        // Clean up: remove the event listener
                        input.removeEventListener('change', handleFileSelect);
                        // Reset input value so same file can be selected again
                        setTimeout(() => {
                            input.value = '';
                        }, 100);
                        resolve(selectedFile);
                    };

                    // Add the event listener
                    input.addEventListener('change', handleFileSelect);

                    // Trigger the file input
                    input.click();

                    // Optional: Add a timeout to resolve with null if user cancels
                    setTimeout(() => {
                        input.removeEventListener('change', handleFileSelect);
                        resolve(null);
                    }, 60000); // 60 second timeout
                });

                // Check if a file was selected
                if (!file) {
                    console.log("No file selected");
                    showToast("No file was selected", "error");
                    return;
                }

                console.log("Selected file:", file);

                // Delete the old document first (optional)
                const doc = documentStatus[docType];

                // Upload the new file
                setLoading(true);
                if (docType === 'kra') {
                    await uploadFile('/extract_kra_pin', file, 'kra');
                } else if (docType === 'police') {
                    await uploadFile('/extract_police_clearance', file, 'police');
                }

            }
        });
    };

    const handleSubmitData = async () => {
        setErrors(prev => ({ ...prev, nameMatch: '' }));

        const newErrors = {};
        if (!kraPin) newErrors.kraPin = 'KRA PIN is required';
        if (!policeClearance) newErrors.policeClearance = 'Police clearance is required';
        if (!idNumber) newErrors.idNumber = 'ID number is required';
        if (!taxPayerName) newErrors.taxPayerName = 'Tax payer name is required';

        if (Object.keys(newErrors).length > 0) {
            setErrors(newErrors);
            return;
        }

        setConfirmDialog({
            isOpen: true,
            title: 'Submit Documents',
            message: 'Are you sure you want to submit these documents? Please verify all information is correct.',
            type: 'success',
            onConfirm: async () => {
                setConfirmDialog(prev => ({ ...prev, isOpen: false }));
                setLoading(true);

                try {
                    // Call the backend submit endpoint
                    const response = await fetch(`${config.API_URL}/document/submit`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            kraPin: kraPin,
                            policeClearance: policeClearance,
                            taxPayerName: taxPayerName,
                            idNumber: idNumber
                        })
                    });

                    const result = await response.json();

                    if (!response.ok || !result.success) {
                        throw new Error('Submission failed');
                    }

                    showToast('Documents submitted successfully!', 'success');
                    resetForm();

                    if (onSubmitSuccess) {
                        onSubmitSuccess();
                    }

                    if (onClose) {
                        onClose();
                    }
                } catch (err) {
                    console.error('Submit error:', err);
                    showToast(err.message || 'Submission failed.', 'error');
                } finally {
                    setLoading(false);
                }
            }
        });
    };

    const resetForm = () => {
        setKraPin('');
        setPoliceClearance('');
        setTaxPayerName('');
        setEmail('');
        setClearedUserName('');
        setIdNumber(user?.idnumber || '');
        setErrors({});
        setDocumentStatus({
            kra: { uploaded: false, fileName: '', fileUrl: '', documentId: null },
            police: { uploaded: false, fileName: '', fileUrl: '', documentId: null }
        });
        resetFileInput(policeClearanceFileRef);
        resetFileInput(kraPinFileRef);
    };

    const resetPoliceClearance = () => {
        setPoliceClearance('');
        setClearedUserName('');
        setDocumentStatus(prev => ({
            ...prev,
            police: { uploaded: false, fileName: '', fileUrl: '', documentId: null }
        }));
        resetFileInput(policeClearanceFileRef);
    };

    const resetFileInput = (ref) => {
        if (ref.current) ref.current.value = '';
    };

    const FileUploadArea = ({
        label,
        icon,
        fileRef,
        onChange,
        value,
        error,
        docType,
        isIdNumber = false
    }) => {
        const doc = documentStatus[docType];
        const isUploaded = doc?.uploaded;

        return (
            <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700">{label}</label>

                {!isIdNumber && (
                    <div className="relative">
                        <input
                            type="text"
                            value={value}
                            readOnly
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-gray-50 text-gray-900"
                            placeholder={`${label} will appear here after upload`}
                        />
                        {value && (
                            <CheckCircle className="absolute right-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-green-500" />
                        )}
                    </div>
                )}

                {isIdNumber && (
                    <div className="relative">
                        <input
                            type="text"
                            value={value}
                            readOnly={!!user?.idnumber}
                            onChange={onChange}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white text-gray-900"
                            placeholder={`Enter ${label.toLowerCase()}`}
                        />
                        {value && (
                            <CheckCircle className="absolute right-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-green-500" />
                        )}
                    </div>
                )}

                {fileRef && (
                    <>
                        {!isUploaded ? (
                            <div
                                className="relative border-2 border-dashed border-gray-300 rounded-md p-4 hover:border-blue-500 hover:bg-blue-50 cursor-pointer transition-all"
                                onClick={() => fileRef.current?.click()}
                            >
                                <input
                                    type="file"
                                    accept=".pdf"
                                    ref={fileRef}
                                    onChange={onChange}
                                    className="hidden"
                                />
                                <div className="flex flex-col items-center space-y-2 text-center">
                                    <div className="p-2 bg-blue-100 rounded-full">
                                        {icon}
                                    </div>
                                    <div>
                                        <p className="text-sm font-medium text-gray-700">Upload {label} PDF</p>
                                        <p className="text-xs text-gray-500">Click to browse files</p>
                                    </div>
                                </div>
                            </div>
                        ) : (
                            <div className="border-2 border-green-300 bg-green-50 rounded-md p-4">
                                <div className="flex items-start justify-between">
                                    <div className="flex items-start space-x-3 flex-1">
                                        <div className="p-2 bg-green-100 rounded-full">
                                            <CheckCircle className="h-5 w-5 text-green-600" />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <p className="text-sm font-medium text-gray-900">Document Uploaded</p>
                                            <p className="text-xs text-gray-600 truncate">{doc.fileName}</p>
                                            <div className="flex items-center space-x-1 mt-2">
                                                <button
                                                    onClick={() => handleDownload(docType)}
                                                    className="inline-flex items-center space-x-1 px-2 py-1 text-xs font-medium text-blue-700 bg-blue-100 rounded hover:bg-blue-200 transition-colors"
                                                >
                                                    <Download className="h-3 w-3" />
                                                    <span>Download</span>
                                                </button>
                                                <button
                                                    onClick={() => handleReupload(docType)}
                                                    className="inline-flex items-center space-x-1 px-2 py-1 text-xs font-medium text-orange-700 bg-orange-100 rounded hover:bg-orange-200 transition-colors"
                                                >
                                                    <RefreshCw className="h-3 w-3" />
                                                    <span>Re-upload</span>
                                                </button>
                                                <button
                                                    onClick={() => handleDelete(docType)}
                                                    className="inline-flex items-center space-x-1 px-2 py-1 text-xs font-medium text-red-700 bg-red-100 rounded hover:bg-red-200 transition-colors"
                                                >
                                                    <Trash2 className="h-3 w-3" />
                                                    <span>Delete</span>
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}
                    </>
                )}

                {error && (
                    <div className="flex items-center space-x-2 text-red-600 text-sm">
                        <AlertCircle className="h-4 w-4" />
                        <span>{error}</span>
                    </div>
                )}
            </div>
        );
    };

    if (!isOpen) return null;

    return (
        <>
            <div className="fixed inset-0 bg-gradient-to-br from-black/60 via-black/50 to-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                <div className="bg-white backdrop-blur-lg rounded-2xl shadow-2xl border border-white/20 p-8 w-full max-w-2xl transform transition-all duration-300 scale-100 max-h-[90vh] overflow-y-auto">
                    <div className="flex justify-between items-center mb-6">
                        <h2 className="text-lg font-semibold text-gray-900">Document Submission</h2>
                        <button
                            onClick={onClose}
                            className="text-gray-500 hover:text-gray-700 transition-colors"
                        >
                            <X className="h-6 w-6" />
                        </button>
                    </div>

                    {errors.nameMatch && (
                        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md flex items-center space-x-2">
                            <AlertCircle className="h-5 w-5 text-red-600" />
                            <span className="text-sm text-red-800 font-medium">{errors.nameMatch}</span>
                        </div>
                    )}

                    <div className="space-y-4 relative">
                        {loading && (
                            <div className="absolute inset-0 bg-white/80 backdrop-blur-sm flex items-center justify-center z-50 rounded-xl">
                                <div className="bg-white p-4 rounded-xl shadow-lg flex items-center space-x-3">
                                    <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
                                    <span className="text-sm font-medium text-gray-700">Processing...</span>
                                </div>
                            </div>
                        )}

                        <FileUploadArea
                            label="KRA PIN"
                            icon={<FileText className="h-5 w-5 text-blue-600" />}
                            fileRef={kraPinFileRef}
                            onChange={(e) => uploadFile('/extract_kra_pin', e.target.files[0], 'kra')}
                            value={kraPin}
                            error={errors.kraPin}
                            docType="kra"
                        />

                        <FileUploadArea
                            label="Police Clearance"
                            icon={<Shield className="h-5 w-5 text-blue-600" />}
                            fileRef={policeClearanceFileRef}
                            onChange={(e) => uploadFile('/extract_police_clearance', e.target.files[0], 'police')}
                            value={policeClearance}
                            error={errors.policeClearance}
                            docType="police"
                        />

                        <FileUploadArea
                            label="ID Number"
                            icon={<FileText className="h-5 w-5 text-blue-600" />}
                            fileRef={null}
                            onChange={(e) => {
                                setIdNumber(e.target.value);
                                setErrors(prev => ({ ...prev, idNumber: '' }));
                            }}
                            value={idNumber}
                            error={errors.idNumber}
                            isIdNumber={true}
                        />

                        <input
                            type="file"
                            accept=".pdf"
                            ref= {genericFileRef}
                            className="hidden"
                        />

                        {errors.submit && (
                            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md flex items-center space-x-2">
                                <AlertCircle className="h-5 w-5 text-red-600" />
                                <span className="text-sm text-red-800 font-medium">{errors.submit}</span>
                            </div>
                        )}
                    </div>

                    <div className="mt-6 flex space-x-4">
                        <button
                            type="button"
                            onClick={handleSubmitData}
                            disabled={loading ||
                                !kraPin ||
                                !policeClearance ||
                                !idNumber ||
                                !taxPayerName
                                || errors.nameMatch.length > 0}
                            className="flex-1 bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                        >
                            Submit Documents
                        </button>
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-6 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 transition-colors font-medium"
                        >
                            Cancel
                        </button>
                    </div>
                </div>
            </div>

            <ConfirmationDialog
                isOpen={confirmDialog.isOpen}
                onClose={() => setConfirmDialog(prev => ({ ...prev, isOpen: false }))}
                onConfirm={confirmDialog.onConfirm}
                title={confirmDialog.title}
                message={confirmDialog.message}
                type={confirmDialog.type}
            />
        </>
    );
};

export default KYCDocumentUploadPage;