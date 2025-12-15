import React from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface PaymentVerificationCardProps {
    onVerify: () => void;
    isLoading: boolean;
}

export const PaymentVerificationCard: React.FC<PaymentVerificationCardProps> = ({ onVerify, isLoading }) => {
    return (
        <Card className="w-full max-w-md bg-yellow-50 border-yellow-400 my-4 shadow-md animate-in fade-in slide-in-from-bottom-4">
            <CardHeader className="pb-2">
                <CardTitle className="text-yellow-700 font-bold flex items-center gap-2">
                    ⚠️ Verification Required
                </CardTitle>
            </CardHeader>
            <CardContent>
                <p className="text-sm text-yellow-800 mb-4">
                    The waiter has paused the transaction to verify your transfer.
                    Please ensure you have sent the money to the account below.
                </p>
                <div className="bg-white p-3 rounded border border-yellow-200 mb-4 text-sm shadow-sm">
                    <div className="grid grid-cols-[60px_1fr] gap-1">
                        <span className="font-semibold text-gray-500">Bank:</span>
                        <span className="font-medium">First Bank</span>
                        <span className="font-semibold text-gray-500">Acct:</span>
                        <span className="font-mono text-lg font-bold">3123456789</span>
                        <span className="font-semibold text-gray-500">Name:</span>
                        <span className="font-medium">Evolution Restaurant</span>
                    </div>
                </div>

                <div className="text-xs text-center text-gray-500 mb-4">
                    * This is a simulated environment. Click Verify to simulate Admin approval. *
                </div>

                <Button
                    onClick={onVerify}
                    disabled={isLoading}
                    className="w-full bg-yellow-600 hover:bg-yellow-700 text-white font-semibold transition-all"
                >
                    {isLoading ? "Verifying..." : "✅ Confirm Verification"}
                </Button>
            </CardContent>
        </Card>
    );
};
