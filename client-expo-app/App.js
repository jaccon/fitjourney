import React, { useState, useEffect } from 'react';
import { StyleSheet, Text, View, TextInput, Button, Alert, FlatList, TouchableOpacity } from 'react-native';
import { Accelerometer } from 'expo-sensors';
import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Network from 'expo-network';

import styles from './styles';

export default function App() {
  const [accelerometerData, setAccelerometerData] = useState({});
  const [stepCount, setStepCount] = useState(0);
  const [previousMagnitude, setPreviousMagnitude] = useState(0);
  const [ipAddress, setIpAddress] = useState('');
  const [port, setPort] = useState('');
  const [savedAddresses, setSavedAddresses] = useState([]);
  const [isWalking, setIsWalking] = useState(false);
  const [message, setMessage] = useState('');
  const [wifiIp, setWifiIp] = useState('');

  useEffect(() => {
    const loadServerAddresses = async () => {
      try {
        const saved = await AsyncStorage.getItem('serverAddresses');
        if (saved) {
          setSavedAddresses(JSON.parse(saved));
        }
      } catch (error) {
        console.error('Erro ao carregar endereços do servidor:', error);
      }
    };

    const getWifiIp = async () => {
      try {
        const ip = await Network.getIpAddressAsync();
        setWifiIp(ip);
      } catch (error) {
        console.error('Erro ao obter IP do Wi-Fi:', error);
      }
    };

    loadServerAddresses();
    getWifiIp();
  }, []);

  useEffect(() => {
    Accelerometer.setUpdateInterval(100);

    const subscription = Accelerometer.addListener(data => {
      setAccelerometerData(data);
    });

    return () => {
      subscription && subscription.remove();
    };
  }, []);

  useEffect(() => {
    const { x, y, z } = accelerometerData;
    const magnitude = Math.sqrt(x * x + y * y + z * z);
    const stepThreshold = 1.2;

    if (magnitude > stepThreshold && previousMagnitude <= stepThreshold) {
      setStepCount(stepCount + 1);
      if (!isWalking) {
        setIsWalking(true);
        console.log('Enviando play...');
        sendActionToServer('play', stepCount + 1); // Enviar o número atualizado de passos
      }
    } else if (magnitude <= stepThreshold && previousMagnitude > stepThreshold) {
      setIsWalking(false);
      console.log('Enviando pause...');
      sendActionToServer('pause', stepCount); // Enviar o número atual de passos
    }

    setPreviousMagnitude(magnitude);
  }, [accelerometerData]);

  const saveServerAddress = async () => {
    if (ipAddress.trim() === '' || port.trim() === '') {
      Alert.alert('Erro', 'Por favor, insira o endereço IP e a porta do servidor.');
    } else {
      const serverAddress = `${ipAddress}:${port}`;
      try {
        const updatedAddresses = [...savedAddresses, serverAddress];
        setSavedAddresses(updatedAddresses);
        await AsyncStorage.setItem('serverAddresses', JSON.stringify(updatedAddresses));
        Alert.alert('Sucesso', 'Endereço do servidor salvo.');
      } catch (error) {
        console.error('Erro ao salvar endereço do servidor:', error);
      }
    }
  };

  const removeServerAddress = async (address) => {
    try {
      const updatedAddresses = savedAddresses.filter(addr => addr !== address);
      setSavedAddresses(updatedAddresses);
      await AsyncStorage.setItem('serverAddresses', JSON.stringify(updatedAddresses));
      Alert.alert('Sucesso', 'Endereço do servidor removido.');
    } catch (error) {
      console.error('Erro ao remover endereço do servidor:', error);
    }
  };

  const sendActionToServer = async (action, steps = 0) => {
    if (!ipAddress || !port) {
      return;
    }
  
    const url = `http://${ipAddress}:${port}/control`;
    const data = `action=${action}&steps=${steps}`;
  
    try {
      console.log(`Enviando ação ${action} com ${steps} passos para ${url}`);
      const response = await axios.post(url, data, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        }
      });
      console.log('Resposta do servidor:', response.data);
      setMessage(`Enviado: ${action}`);
    } catch (error) {
      console.error('Erro ao enviar ação para o servidor:', error.message);
    }
  };

  const { x, y, z } = accelerometerData;

  return (
    <View style={styles.container}>
      <Text style={styles.header}>Contador de Passos</Text>
      <Text style={styles.wifiIp}>IP do Wi-Fi: {wifiIp}</Text>
      <TextInput
        style={styles.input}
        placeholder="Endereço IP do servidor"
        value={ipAddress}
        onChangeText={setIpAddress}
      />
      <TextInput
        style={styles.input}
        placeholder="Porta do servidor"
        value={port}
        onChangeText={setPort}
        keyboardType="numeric"
      />
      <Button title="Salvar Endereço" onPress={saveServerAddress} />
      {savedAddresses.length > 0 && (
        <FlatList
          data={savedAddresses}
          keyExtractor={(item, index) => index.toString()}
          renderItem={({ item }) => (
            <View style={styles.addressRow}>
              <TouchableOpacity onPress={() => {
                const [ip, port] = item.split(':');
                setIpAddress(ip);
                setPort(port);
              }}>
                <Text style={styles.addressText}>{item}</Text>
              </TouchableOpacity>
              <Button title="Remover" onPress={() => removeServerAddress(item)} color="red" />
            </View>
          )}
        />
      )}
      <Text style={styles.stepCount}>Passos: {stepCount}</Text>
      <Text style={styles.subHeader}>Acelerômetro:</Text>
      <Text style={styles.data}>X: {x ? x.toFixed(2) : 'N/A'}</Text>
      <Text style={styles.data}>Y: {y ? y.toFixed(2) : 'N/A'}</Text>
      <Text style={styles.data}>Z: {z ? z.toFixed(2) : 'N/A'}</Text>
    </View>
  );
}
