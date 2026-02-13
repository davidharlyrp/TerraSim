import React, { createContext, useContext, useEffect, useState } from 'react';
import { pb } from '../pb';
import { AuthModel } from 'pocketbase';

interface AuthContextType {
    user: AuthModel | null;
    isValid: boolean;
    loginWithGoogle: () => Promise<void>;
    logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [user, setUser] = useState<AuthModel | null>(pb.authStore.model);
    const [isValid, setIsValid] = useState(pb.authStore.isValid);

    useEffect(() => {
        return pb.authStore.onChange((token, model) => {
            setUser(model);
            setIsValid(!!token);
        });
    }, []);

    const loginWithGoogle = async () => {
        try {
            await pb.collection('users').authWithOAuth2({ provider: 'google' });
        } catch (error) {
            console.error("Login failed", error);
            throw error;
        }
    };

    const logout = () => {
        pb.authStore.clear();
    };

    return (
        <AuthContext.Provider value={{ user, isValid, loginWithGoogle, logout }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) throw new Error("useAuth must be used within an AuthProvider");
    return context;
};
