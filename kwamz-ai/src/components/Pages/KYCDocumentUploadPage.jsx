import React, { useState, useRef, useEffect } from 'react';
import { Upload, FileText, Shield, CreditCard, X, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { useToast } from './ToastProvider';
import axios from 'axios';
import config from '../../Config';

const KYCDocumentUploadPage = ({ isOpen = true, onClose = () => { }, user = { idnumber: '12345678' }, onSubmitSuccess }) => {
    const [kraPin, setKraPin] = useState('');
    const [taxPayerName, setTaxPayerName] = useState('');
    const [policeClearance, setPoliceClearance] = useState('');
    const [clearedUserName, setClearedUserName] = useState('');
    const [idNumber, setIdNumber] = useState(user?.idnumber || '');
    const [message, setMessage] = useState('');
    const [showModal, setShowModal] = useState(false);
    const [loading, setLoading] = useState(false);
    const [uploadProgress, setUploadProgress] = useState({});
    const [errors, setErrors] = useState({});
    const { showToast } = useToast();

    const kraPinFileRef = useRef(null);
    const policeClearanceFileRef = useRef(null);

    useEffect(() => {
        if (taxPayerName && clearedUserName) {
            if (taxPayerName !== clearedUserName) {
                showToast('The taxpayer name does not match police clearance form details', 'error');
                setTimeout(() => {
                    setErrors(prev => ({ ...prev, nameMatch: '' }));
                    resetPoliceClearance();
                }, 3000);
            } else {
                setErrors(prev => ({ ...prev, nameMatch: '' }));
            }
        }
    }, [taxPayerName, clearedUserName]);

    useEffect(() => {
        if (user?.idnumber) {
            setIdNumber(user.idnumber);
        }
    }, [user]);

    const validatePhone = (phone) => /^\d{10,}$/.test(phone);

    const resetPoliceClearance = () => {
        setPoliceClearance('');
        setClearedUserName('');
        resetFileInput(policeClearanceFileRef);
    };


    const uploadFile = async (endpoint, file, fieldMap) => {

        if (!file) return;
        const formData = new FormData();
        formData.append('file', file);
        setLoading(true);
        try {
            const res = await fetch(`${config.API_URL}/document${endpoint}`, { method: 'POST', body: formData });
            const result = await res.json();
            if (result.error) {
                alert(result.error);
                return;
            }
            fieldMap.forEach(({ id, key }) => {
                console.log("the key is", key)
                if (key === 'kraPin') setKraPin(result[key]);
                if (key === 'taxPayerName') setTaxPayerName(result[key]);
                if (key === 'refNo') setPoliceClearance(result[key]);
                if (key === 'name') setClearedUserName(result[key]);
                if (key === 'idNo') setIdNumber(result[key]);
            });

        } catch (err) {
            console.error('Upload failed:', err);
            alert('File upload failed.');
        } finally {
            setLoading(false);
        }
    };

    const handleSubmitData = async () => {
        setErrors({});

        const newErrors = {};
        if (!kraPin) newErrors.kraPin = 'KRA PIN is required';
        if (!policeClearance) newErrors.policeClearance = 'Police clearance is required';
        if (!idNumber) newErrors.idNumber = 'ID number is required';
        if (!taxPayerName) newErrors.taxPayerName = 'Tax payer name is required';

        if (Object.keys(newErrors).length > 0) {
            setErrors(newErrors);
            return;
        }

        const payload = { kraPin, policeClearance, idNumber, taxPayerName };
        setLoading(true);


        try {
            const res = await fetch(`${config.API_URL}/document/submit`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            const result = await res.json();

            if (res.ok) {
                // alert(result.message || result.success || 'Submission complete');
                showToast(result.message || result.success || 'Documents submitted successfully!', 'success');
                resetForm();

                // Call the success callback if provided
                if (onSubmitSuccess) {
                    onSubmitSuccess();
                }

                // Close the form after successful submission
                if (onClose) {
                    onClose();
                }
            } else {
                throw new Error(result.error || 'Submission failed');
            }
        } catch (err) {
            console.error('Submit error:', err);
            showToast(err.message || 'Submission failed.', 'error');
        } finally {
            setLoading(false);
        }
    };


    const resetForm = () => {
        setKraPin('');
        setPoliceClearance('');
        setTaxPayerName('');
        setClearedUserName('');
        setIdNumber(user?.idnumber || '');
        setMessage('');
        setErrors({});
        setUploadProgress({});
        resetFileInput(policeClearanceFileRef);
        resetFileInput(kraPinFileRef);
    };

    const resetFileInput = (ref) => {
        if (ref.current) ref.current.value = '';
    };

    const handleSubmit = async (response) => {
        const checkout_id = response.CheckoutRequestID;
        setLoading(true);

        // Simulate payment processing
        await new Promise(resolve => setTimeout(resolve, 3000));

        // Simulate successful payment
        await handleSubmitData();
        setLoading(false);
        setShowModal(false);
    };

    const FileUploadArea = ({ label, icon, fileRef, onChange, value, error, progress, fileType }) => (
        <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700">{label}</label>
            <div className="relative">
                <input
                    type="text"
                    value={value}
                    readOnly={fileType === 'idNumber' && user?.idnumber}
                    onChange={onChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white text-gray-900"
                    placeholder={`Enter ${label.toLowerCase()}`}
                />
                {value && (
                    <CheckCircle className="absolute right-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-green-500" />
                )}
            </div>

            {fileRef && (
                <div
                    className="relative border-2 border-dashed border-gray-300 rounded-md p-4 hover:border-blue-500 hover:bg-gray-50 cursor-pointer"
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

                    {progress !== null && (
                        <div className="mt-3">
                            <div className="flex justify-between text-xs text-gray-600">
                                <span>Uploading...</span>
                                <span>{progress}%</span>
                            </div>
                            <div className="w-full bg-gray-200 rounded-full h-2 mt-1">
                                <div
                                    className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                                    style={{ width: `${progress}%` }}
                                />
                            </div>
                        </div>
                    )}
                </div>
            )}

            {error && (
                <div className="flex items-center space-x-2 text-red-600 text-sm">
                    <AlertCircle className="h-4 w-4" />
                    <span>{error}</span>
                </div>
            )}
        </div>
    );

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-gradient-to-br from-black/60 via-black/50 to-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-white backdrop-blur-lg rounded-2xl shadow-2xl border border-white/20 p-8 w-full max-w-2xl transform transition-all duration-300 scale-100 max-h-[90vh] overflow-y-auto">
                <div className="flex justify-between items-center mb-6">
                    <h2 className="text-lg font-semibold text-gray-900">Document Submission</h2>
                    <button
                        onClick={onClose}
                        className="text-gray-500 hover:text-gray-700"
                    >
                        <X className="h-6 w-6" />
                    </button>
                </div>

                {message && (
                    <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-md flex items-center space-x-2">
                        <CheckCircle className="h-5 w-5 text-green-600" />
                        <span className="text-sm text-green-800 font-medium">{message}</span>
                    </div>
                )}

                {errors.nameMatch && (
                    <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md flex items-center space-x-2">
                        <AlertCircle className="h-5 w-5 text-red-600" />
                        <span className="text-sm text-red-800 font-medium">{errors.nameMatch}</span>
                    </div>
                )}

                <div className="space-y-4 relative">
                    {loading && (
                        <div className="absolute inset-0 bg-white bg-opacity-5 backdrop-blur-[2px] flex items-center justify-center z-50 rounded-xl">
                            <div className="bg-white bg-opacity-30 p-4 rounded-xl shadow-lg flex items-center space-x-2 backdrop-blur-md border border-white border-opacity-20">
                                <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
                                <span className="text-sm font-medium text-gray-700">Processing...</span>
                            </div>
                        </div>
                    )}
                    <FileUploadArea
                        label="KRA PIN"
                        icon={<FileText className="h-5 w-5 text-blue-600" />}
                        fileRef={kraPinFileRef}
                        onChange={(e) =>
                            uploadFile('/extract_kra_pin', e.target.files[0], [
                                { id: 'kraPin', key: 'kraPin' },
                                { id: 'taxPayerName', key: 'taxPayerName' },
                            ], 'kra')
                        }
                        value={kraPin}
                        error={errors.kraPin || errors.kra}
                        progress={uploadProgress.kra}
                        fileType="kra"
                    />

                    <FileUploadArea
                        label="Police Clearance"
                        icon={<Shield className="h-5 w-5 text-blue-600" />}
                        fileRef={policeClearanceFileRef}
                        onChange={(e) =>
                            uploadFile('/extract_police_clearance', e.target.files[0], [
                                { id: 'policeClearance', key: 'refNo' },
                                { id: 'name', key: 'name' },
                                { id: 'idNumber', key: 'idNo' },
                            ], 'police')
                        }
                        value={policeClearance}
                        error={errors.policeClearance || errors.police}
                        progress={uploadProgress.police}
                        fileType="police"
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
                        progress={null}
                        fileType="idNumber"
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
                        onClick={() => handleSubmitData()}
                        disabled={loading || !kraPin || !policeClearance || !idNumber || !taxPayerName}
                        className="flex-1 bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        Submit
                    </button>
                    <button
                        type="button"
                        onClick={onClose}
                        className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 transition-colors"
                    >
                        Cancel
                    </button>
                </div>
            </div>
        </div>
    );
};

export default KYCDocumentUploadPage;