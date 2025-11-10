from .base import ReservaBase
from sqlalchemy import text
from datetime import datetime

class ReservaMuelle(ReservaBase):
    
    def crear_reserva(self, datos):
        print("📥 Datos recibidos:", datos)

        # 1. Validar campos obligatorios
        requeridos = ["usuario_id", "tenant_id", "lugar_id", "fecha_entrada", "fecha_salida", "tipo_embarcacion"]
        for campo in requeridos:
            if campo not in datos or not datos[campo]:
                return {"error": f"El campo {campo} es obligatorio"}, 400

        try:
            # 2. Agregar la fecha de reserva (fecha actual)
            from datetime import datetime
            datos['fecha'] = datetime.now().strftime('%Y-%m-%d')

            # 3. Validar disponibilidad antes de crear
            lugar_id = datos["lugar_id"]
            fecha_entrada = datos["fecha_entrada"]
            fecha_salida = datos["fecha_salida"]

            # Verificar que el lugar existe y pertenece al tenant
            query_lugar = text("""
                SELECT capacidad FROM lugares 
                WHERE id = :lugar_id AND tenant_id = :tenant_id
            """)
            capacidad = self.db.execute(query_lugar, {
                "lugar_id": lugar_id,
                "tenant_id": datos["tenant_id"]
            }).scalar()

            if not capacidad:
                return {"error": "El lugar no existe o no pertenece a este negocio"}, 404

            # Verificar disponibilidad
            query_ocupacion = text("""
                SELECT COUNT(*) FROM reservas_generales rg
                JOIN reservas_muelle rm ON rg.id = rm.reserva_id
                WHERE rg.lugar_id = :lugar_id
                  AND rg.tenant_id = :tenant_id
                  AND daterange(rm.fecha_entrada, rm.fecha_salida, '[]') &&
                      daterange(:fecha_entrada, :fecha_salida, '[]')
            """)
            ocupadas = self.db.execute(query_ocupacion, {
                "lugar_id": lugar_id,
                "tenant_id": datos["tenant_id"],
                "fecha_entrada": fecha_entrada,
                "fecha_salida": fecha_salida
            }).scalar()

            if ocupadas >= capacidad:
                return {"error": "No hay disponibilidad en ese rango de fechas"}, 409

            # 4. Insertar en reservas_generales
            query_reserva_general = text("""
                INSERT INTO reservas_generales (usuario_id, lugar_id, fecha, tenant_id)
                VALUES (:usuario_id, :lugar_id, :fecha, :tenant_id)
                RETURNING id
            """)
            
            reserva_id = self.db.execute(query_reserva_general, {
                "usuario_id": datos["usuario_id"],
                "lugar_id": datos["lugar_id"],
                "fecha": datos["fecha"],
                "tenant_id": datos["tenant_id"]
            }).scalar()

            # 5. Insertar en reservas_muelle
            query_reserva_muelle = text("""
                INSERT INTO reservas_muelle (
                    reserva_id, fecha_entrada, fecha_salida, tipo_embarcacion,
                    requiere_pintura, requiere_mecanica, requiere_motor
                ) VALUES (
                    :reserva_id, :fecha_entrada, :fecha_salida, :tipo_embarcacion,
                    :requiere_pintura, :requiere_mecanica, :requiere_motor
                )
            """)
            
            self.db.execute(query_reserva_muelle, {
                "reserva_id": reserva_id,
                "fecha_entrada": datos["fecha_entrada"],
                "fecha_salida": datos["fecha_salida"],
                "tipo_embarcacion": datos["tipo_embarcacion"],
                "requiere_pintura": datos.get("requiere_pintura", False),
                "requiere_mecanica": datos.get("requiere_mecanica", False),
                "requiere_motor": datos.get("requiere_motor", False)
            })

            # 6. Confirmar la transacción
            self.db.commit()

            print(f"✅ Reserva creada exitosamente con ID: {reserva_id}")
            return {
                "mensaje": "Reserva creada exitosamente",
                "reserva_id": reserva_id,
                "fecha": datos["fecha"]
            }, 201

        except Exception as e:
            # Rollback en caso de error
            self.db.rollback()
            print(f"❌ Error al crear reserva: {str(e)}")
            return {"error": f"Error interno del servidor: {str(e)}"}, 500

    
    def listar_reservas(self, usuario_id=None):
        try:
            query = text("""
                SELECT rg.id AS reserva_id,
                       TO_CHAR(rg.fecha, 'YYYY-MM-DD') AS fecha,
                       TO_CHAR(rm.fecha_entrada, 'YYYY-MM-DD') AS fecha_entrada,
                       TO_CHAR(rm.fecha_salida, 'YYYY-MM-DD') AS fecha_salida,
                       rm.tipo_embarcacion,
                       rm.requiere_pintura,
                       rm.requiere_mecanica,
                       rm.requiere_motor,
                       u.nombre AS usuario,
                       l.nombre AS lugar,
                       rg.usuario_id,
                       rg.lugar_id
                FROM reservas_generales rg
                JOIN reservas_muelle rm ON rg.id = rm.reserva_id
                JOIN usuarios u ON rg.usuario_id = u.id
                LEFT JOIN lugares l ON rg.lugar_id = l.id
                WHERE rg.tenant_id = :tenant_id 
                  AND (:usuario_id IS NULL OR rg.usuario_id = :usuario_id)
                ORDER BY rm.fecha_entrada DESC
            """)
            result = self.db.execute(query, {
                "tenant_id": self.tenant_id,
                "usuario_id": usuario_id # <-- Usamos el argumento
            }).mappings()
            
            reservas = [dict(row) for row in result]
            print(f"🔍 Filtrando por usuario_id: {usuario_id}. Reservas encontradas: {len(reservas)}")
            return reservas
            
        except Exception as e:
            print(f"❌ Error al listar reservas: {str(e)}")
            return {"error": str(e)}

    def consultar_disponibilidad_por_dias(self, fecha_inicio, fecha_fin):
        try:
            query = text("""
                WITH dias AS (
                    SELECT generate_series(:fecha_inicio, :fecha_fin, interval '1 day')::date AS dia
                ),
                ocupacion AS (
                    SELECT
                        l.id AS lugar_id,
                        l.nombre AS nombre,
                        l.capacidad AS capacidad,
                        d.dia,
                        COUNT(DISTINCT rm.reserva_id) AS ocupadas
                    FROM lugares l
                    JOIN dias d ON TRUE
                    LEFT JOIN reservas_generales rg ON l.id = rg.lugar_id
                    LEFT JOIN reservas_muelle rm ON rg.id = rm.reserva_id
                        AND d.dia BETWEEN rm.fecha_entrada AND rm.fecha_salida
                    WHERE l.tenant_id = :tenant_id
                    GROUP BY l.id, l.nombre, l.capacidad, d.dia
                    ORDER BY l.id, d.dia
                )
                SELECT * FROM ocupacion
            """)

            rows = self.db.execute(query, {
                "tenant_id": self.tenant_id,
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin
            }).fetchall()

            from datetime import datetime, timedelta

            def calcular_tramos_con_cupos(disponibles_por_dia):
                fechas = sorted(disponibles_por_dia.keys())
                tramos = []
                inicio = None
                fin = None
                min_cupos = None

                for fecha_str in fechas:
                    disponibles = disponibles_por_dia[fecha_str]
                    fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()

                    if disponibles > 0:
                        if inicio is None:
                            inicio = fecha
                            fin = fecha
                            min_cupos = disponibles
                        elif fecha == fin + timedelta(days=1):
                            fin = fecha
                            min_cupos = min(min_cupos, disponibles)
                        else:
                            tramos.append({
                                "inicio": inicio.strftime("%Y-%m-%d"),
                                "fin": fin.strftime("%Y-%m-%d"),
                                "cupos": min_cupos
                            })
                            inicio = fecha
                            fin = fecha
                            min_cupos = disponibles
                    else:
                        if inicio is not None:
                            tramos.append({
                                "inicio": inicio.strftime("%Y-%m-%d"),
                                "fin": fin.strftime("%Y-%m-%d"),
                                "cupos": min_cupos
                            })
                            inicio = None
                            fin = None
                            min_cupos = None

                if inicio is not None:
                    tramos.append({
                        "inicio": inicio.strftime("%Y-%m-%d"),
                        "fin": fin.strftime("%Y-%m-%d"),
                        "cupos": min_cupos
                    })

                # Detectar si hay días completamente libres después del último tramo
                if fechas:
                    ultima_fecha = datetime.strptime(fechas[-1], "%Y-%m-%d").date()
                    if disponibilidad_total_desde(ultima_fecha + timedelta(days=1)):
                        tramos.append({
                            "inicio_abierta": (ultima_fecha + timedelta(days=1)).strftime("%Y-%m-%d")
                        })

                return tramos

            def disponibilidad_total_desde(fecha):
               # puedes mejorar esto según tu sistema (ej. revisar si hay reservas futuras)
               return True  # Por ahora asumimos que desde el día siguiente no hay reservas
            # Agrupar por lugar y aplicar lógica de tramos
            disponibilidad = []
            por_lugar = {}

            for row in rows:
                lugar_id = row.lugar_id
                dia_str = row.dia.strftime("%Y-%m-%d")
                disponibles = row.capacidad - row.ocupadas

                if lugar_id not in por_lugar:
                    por_lugar[lugar_id] = {
                        "lugar_id": lugar_id,
                        "nombre": row.nombre,
                        "capacidad": row.capacidad,
                        "disponibles_por_dia": {}
                    }

                por_lugar[lugar_id]["disponibles_por_dia"][dia_str] = disponibles

            # En el ciclo final
            for lugar in por_lugar.values():
                lugar["tramos_disponibles"] = calcular_tramos_con_cupos(lugar["disponibles_por_dia"])
                del lugar["disponibles_por_dia"]
                disponibilidad.append(lugar)
            
            return disponibilidad

        except Exception as e:
            return {"error": str(e)}
