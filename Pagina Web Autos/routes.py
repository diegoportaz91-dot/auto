import os
import json
import hashlib
import secrets
from flask import render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from app import app, db
from models import Vehicle, Admin, Click, VehicleView, ClientRequest, PageVisit
from datetime import datetime
import urllib.parse

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_password_hash_sha256(password):
    """Genera un hash SHA-256 de la contraseña con salt"""
    # Generar un salt aleatorio
    salt = secrets.token_hex(16)
    
    # Combinar contraseña con salt
    salted_password = password + salt
    
    # Generar hash SHA-256
    password_hash = hashlib.sha256(salted_password.encode()).hexdigest()
    
    # Combinar salt y hash
    full_hash = salt + password_hash
    
    return full_hash

def verify_password_sha256(password, stored_hash):
    """Verifica una contraseña contra su hash SHA-256 almacenado"""
    if len(stored_hash) < 32:  # Salt debe ser al menos 16 bytes (32 hex chars)
        return False
    
    # Extraer salt (primeros 32 caracteres)
    salt = stored_hash[:32]
    
    # Extraer hash (resto de caracteres)
    password_hash = stored_hash[32:]
    
    # Generar hash de la contraseña ingresada
    salted_password = password + salt
    computed_hash = hashlib.sha256(salted_password.encode()).hexdigest()
    
    # Comparar hashes
    return computed_hash == password_hash

def track_page_visit(page_name):
    """Track page visits for analytics"""
    try:
        # Get client information
        ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR'))
        user_agent = request.headers.get('User-Agent')
        referrer = request.headers.get('Referer')
        
        # Create page visit record
        visit = PageVisit(
            page=page_name,
            ip_address=ip_address,
            user_agent=user_agent,
            referrer=referrer
        )
        
        db.session.add(visit)
        db.session.commit()
    except Exception as e:
        # Log error but don't break the page
        print(f"Error tracking page visit: {e}")
        db.session.rollback()

@app.route('/terminos-y-condiciones')
def terms_conditions():
    from datetime import datetime
    now = datetime.utcnow()
    return render_template('terms_conditions.html', now=now)

@app.route('/')
def index():
    # Track page visit
    track_page_visit('index')
    
    # Get search and filter parameters
    search_query = request.args.get('search', '').strip()
    price_min = request.args.get('price_min', type=int)
    price_max = request.args.get('price_max', type=int)
    brand = request.args.get('brand', '').strip()
    year_min = request.args.get('year_min', type=int)
    year_max = request.args.get('year_max', type=int)
    location = request.args.get('location', '').strip()
    fuel_type = request.args.get('fuel_type', '').strip()
    transmission = request.args.get('transmission', '').strip()
    km_min = request.args.get('km_min', type=int)
    km_max = request.args.get('km_max', type=int)
    
    # Start with base query
    query = Vehicle.query.filter_by(is_active=True)
    
    # Apply search filter
    if search_query:
        search_filter = f"%{search_query}%"
        query = query.filter(
            db.or_(
                Vehicle.title.ilike(search_filter),
                Vehicle.brand.ilike(search_filter),
                Vehicle.model.ilike(search_filter),
                Vehicle.description.ilike(search_filter)
            )
        )
    
    # Apply price filters
    if price_min is not None:
        query = query.filter(Vehicle.price >= price_min)
    if price_max is not None:
        query = query.filter(Vehicle.price <= price_max)
    
    # Apply brand filter
    if brand:
        query = query.filter(Vehicle.brand.ilike(f"%{brand}%"))
    
    # Apply year filters
    if year_min is not None:
        query = query.filter(Vehicle.year >= year_min)
    if year_max is not None:
        query = query.filter(Vehicle.year <= year_max)
    
    # Apply location filter (assuming location is stored in a field)
    if location:
        query = query.filter(Vehicle.title.ilike(f"%{location}%"))
    
    # Apply fuel type filter
    if fuel_type:
        query = query.filter(Vehicle.fuel_type == fuel_type)
    
    # Apply transmission filter
    if transmission:
        query = query.filter(Vehicle.transmission == transmission)
    
    # Apply kilometers filters
    if km_min is not None:
        query = query.filter(Vehicle.kilometers >= km_min)
    if km_max is not None:
        query = query.filter(Vehicle.kilometers <= km_max)
    
    # Pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Order vehicles randomly for exploration
    import random
    all_vehicles = query.all()
    random.shuffle(all_vehicles)
    
    # Calculate pagination
    total_vehicles = len(all_vehicles)
    start_index = (page - 1) * per_page
    end_index = start_index + per_page
    vehicles = all_vehicles[start_index:end_index]
    
    # Calculate pagination info
    total_pages = (total_vehicles + per_page - 1) // per_page
    has_prev = page > 1
    has_next = page < total_pages
    
    # Get most viewed vehicles for the carousel (only Plus publications)
    from sqlalchemy import func
    most_viewed_vehicles = db.session.query(
        Vehicle,
        func.count(VehicleView.id).label('view_count')
    ).outerjoin(VehicleView).filter(
        Vehicle.is_active == True,
        Vehicle.is_plus == True  # Only Plus publications
    ).group_by(Vehicle.id).order_by(
        func.count(VehicleView.id).desc()
    ).limit(10).all()
    
    # Get unique brands for filter dropdown
    unique_brands = db.session.query(Vehicle.brand).filter(
        Vehicle.is_active == True,
        Vehicle.brand.isnot(None),
        Vehicle.brand != ''
    ).distinct().order_by(Vehicle.brand).all()
    brands = [brand[0] for brand in unique_brands]
    
    return render_template('index.html', 
                         vehicles=vehicles, 
                         most_viewed_vehicles=most_viewed_vehicles,
                         brands=brands,
                         pagination={
                             'page': page,
                             'per_page': per_page,
                             'total_vehicles': total_vehicles,
                             'total_pages': total_pages,
                             'has_prev': has_prev,
                             'has_next': has_next,
                             'prev_num': page - 1 if has_prev else None,
                             'next_num': page + 1 if has_next else None
                         },
                         current_filters={
                             'search': search_query,
                             'price_min': price_min,
                             'price_max': price_max,
                             'brand': brand,
                             'year_min': year_min,
                             'year_max': year_max,
                             'location': location,
                             'fuel_type': fuel_type,
                             'transmission': transmission,
                             'km_min': km_min,
                             'km_max': km_max
                         })

@app.route('/api/search')
def api_search():
    """API endpoint for AJAX search"""
    search_query = request.args.get('q', '').strip()
    
    if not search_query:
        return jsonify({'vehicles': []})
    
    # Search in title, brand, model, and description
    search_filter = f"%{search_query}%"
    vehicles = Vehicle.query.filter(
        Vehicle.is_active == True,
        db.or_(
            Vehicle.title.ilike(search_filter),
            Vehicle.brand.ilike(search_filter),
            Vehicle.model.ilike(search_filter),
            Vehicle.description.ilike(search_filter)
        )
    ).limit(10).all()
    
    # Format results for JSON response
    results = []
    for vehicle in vehicles:
        results.append({
            'id': vehicle.id,
            'title': vehicle.title,
            'brand': vehicle.brand,
            'model': vehicle.model,
            'price': vehicle.format_price(),
            'year': vehicle.year,
            'kilometers': vehicle.kilometers,
            'fuel_type': vehicle.fuel_type,
            'image': vehicle.get_main_image(),
            'url': url_for('vehicle_detail', id=vehicle.id)
        })
    
    return jsonify({'vehicles': results})

@app.route('/vehicle/<int:id>')
def vehicle_detail(id):
    vehicle = Vehicle.query.get_or_404(id)
    
    # Track view
    view = VehicleView(
        vehicle_id=vehicle.id,
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent', '')[:500]
    )
    db.session.add(view)
    db.session.commit()
    
    return render_template('vehicle_detail.html', vehicle=vehicle)

@app.route('/track_click/<int:vehicle_id>/<click_type>')
def track_click(vehicle_id, click_type):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    
    # Track click
    click = Click(
        vehicle_id=vehicle_id,
        click_type=click_type,
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent', '')[:500]
    )
    db.session.add(click)
    db.session.commit()
    
    # Generate WhatsApp URL
    if click_type == 'whatsapp':
        message = vehicle.get_whatsapp_contact_message()
    elif click_type == 'offer':
        offer_amount = request.args.get('offer', '0')
        try:
            offer_amount = int(offer_amount.replace('.', '').replace(',', ''))
        except:
            offer_amount = 0
        message = vehicle.get_whatsapp_offer_message(offer_amount)
    else:
        message = f"Consulta sobre: {vehicle.title}"
    
    whatsapp_url = f"https://wa.me/{vehicle.whatsapp_number.replace('+', '')}?text={urllib.parse.quote(message)}"
    return redirect(whatsapp_url)


@app.route('/panel/login', methods=['GET', 'POST'])
def panel_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        admin = Admin.query.filter_by(username=username).first()
        
        if admin:
            # Verificar contraseña con SHA-256
            if verify_password_sha256(password, admin.password_hash):
                session.permanent = True  # Enable session timeout
                session['admin_logged_in'] = True
                session['admin_id'] = admin.id
                return redirect(url_for('admin_dashboard'))
            else:
                flash('Credenciales inválidas', 'error')
        else:
            flash('Credenciales inválidas', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    session.pop('admin_id', None)
    return redirect(url_for('index'))

@app.route('/panel')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('panel_login'))
    
    # Get statistics
    total_vehicles = Vehicle.query.filter_by(is_active=True).count()
    total_whatsapp_clicks = Click.query.filter_by(click_type='whatsapp').count()
    total_offer_clicks = Click.query.filter_by(click_type='offer').count()
    total_views = VehicleView.query.count()
    pending_requests_count = ClientRequest.query.filter_by(status='pending').count()
    
    # Get page visit statistics
    total_page_visits = PageVisit.query.filter_by(page='index').count()
    today_visits = PageVisit.query.filter(
        PageVisit.page == 'index',
        PageVisit.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    ).count()
    
    # Most viewed vehicles (all publications for admin)
    from sqlalchemy import func
    most_viewed = db.session.query(
        Vehicle,
        func.count(VehicleView.id).label('view_count'),
        func.count(Click.id).label('click_count')
    ).outerjoin(VehicleView).outerjoin(Click).filter(
        Vehicle.is_active == True
    ).group_by(Vehicle.id).order_by(
        func.count(VehicleView.id).desc()
    ).limit(10).all()
    
    stats = {
        'total_vehicles': total_vehicles,
        'total_whatsapp_clicks': total_whatsapp_clicks,
        'total_offer_clicks': total_offer_clicks,
        'total_views': total_views,
        'most_viewed': most_viewed,
        'pending_requests_count': pending_requests_count,
        'total_page_visits': total_page_visits,
        'today_visits': today_visits
    }
    
    return render_template('admin_dashboard.html', stats=stats)

@app.route('/admin/add_vehicle', methods=['GET', 'POST'])
def add_vehicle():
    if not session.get('admin_logged_in'):
        return redirect(url_for('panel_login'))
    
    if request.method == 'POST':
        # Handle form submission
        # Clean price input (remove dots, commas, and spaces)
        price_str = request.form['price'].replace('.', '').replace(',', '').replace(' ', '')
        
        vehicle = Vehicle(
            title=request.form['title'],
            description=request.form['description'],
            price=int(price_str),
            currency=request.form.get('currency', 'ARS'),
            year=int(request.form['year']) if request.form['year'] else None,
            brand=request.form['brand'],
            model=request.form['model'],
            kilometers=int(request.form['kilometers'].replace('.', '').replace(',', '').replace(' ', '')) if request.form['kilometers'] else None,
            fuel_type=request.form['fuel_type'],
            transmission=request.form['transmission'],
            color=request.form['color'],
            whatsapp_number=request.form.get('whatsapp_number', ''),
            call_number=request.form.get('call_number', ''),
            contact_type=request.form.get('contact_type', 'whatsapp'),  # Legacy field
            phone_number=request.form.get('phone_number', '')  # Legacy field
        )
        
        # Handle uploaded images
        image_urls = []
        if 'vehicle_images' in request.files:
            files = request.files.getlist('vehicle_images')
            for file in files:
                if file and file.filename and allowed_file(file.filename):
                    # Generate unique filename
                    filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                    filename = f"{timestamp}_{filename}"
                    
                    # Save file
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    
                    # Store relative URL
                    image_urls.append(f"uploads/{filename}")
        
        vehicle.images = json.dumps(image_urls)
        
        # Set main image index
        main_image_index = int(request.form.get('main_image_index', 0))
        vehicle.main_image_index = main_image_index
        
        db.session.add(vehicle)
        db.session.commit()
        
        flash('Vehículo agregado exitosamente', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('add_vehicle.html')

@app.route('/admin/edit_vehicle/<int:id>', methods=['GET', 'POST'])
def edit_vehicle(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('panel_login'))
    
    vehicle = Vehicle.query.get_or_404(id)
    
    if request.method == 'POST':
        # Update vehicle data
        price_str = request.form['price'].replace('.', '').replace(',', '').replace(' ', '')
        
        vehicle.title = request.form['title']
        vehicle.description = request.form['description']
        vehicle.price = int(price_str)
        vehicle.currency = request.form.get('currency', 'ARS')
        vehicle.year = int(request.form['year']) if request.form['year'] else None
        vehicle.brand = request.form['brand']
        vehicle.model = request.form['model']
        vehicle.kilometers = int(request.form['kilometers'].replace('.', '').replace(',', '').replace(' ', '')) if request.form['kilometers'] else None
        vehicle.fuel_type = request.form['fuel_type']
        vehicle.transmission = request.form['transmission']
        vehicle.color = request.form['color']
        vehicle.whatsapp_number = request.form.get('whatsapp_number', '')
        vehicle.call_number = request.form.get('call_number', '')
        vehicle.contact_type = request.form.get('contact_type', 'whatsapp')  # Legacy field
        vehicle.phone_number = request.form.get('phone_number', '')  # Legacy field
        vehicle.is_plus = request.form.get('is_plus') == 'true'
        
        # Handle new uploaded images
        if 'vehicle_images' in request.files:
            files = request.files.getlist('vehicle_images')
            if any(file.filename for file in files):  # If new images are uploaded
                new_image_urls = []
                for file in files:
                    if file and file.filename and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                        filename = f"{timestamp}_{filename}"
                        
                        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        file.save(file_path)
                        
                        new_image_urls.append(f"uploads/{filename}")
                
                if new_image_urls:  # Replace images only if new ones were uploaded
                    vehicle.images = json.dumps(new_image_urls)
        
        db.session.commit()
        flash('Vehículo actualizado exitosamente', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('edit_vehicle.html', vehicle=vehicle)

@app.route('/admin/delete_vehicle/<int:id>', methods=['POST'])
def delete_vehicle(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('panel_login'))
    
    vehicle = Vehicle.query.get_or_404(id)
    
    # Delete associated images from filesystem
    if vehicle.images:
        image_urls = json.loads(vehicle.images)
        for image_url in image_urls:
            if image_url.startswith('uploads/'):
                image_path = os.path.join('static', image_url)
                if os.path.exists(image_path):
                    try:
                        os.remove(image_path)
                    except OSError:
                        pass  # Ignore if file can't be deleted
    
    # Delete vehicle from database
    db.session.delete(vehicle)
    db.session.commit()
    
    flash('Vehículo eliminado exitosamente', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/solicitar-publicacion', methods=['GET', 'POST'])
def client_request():
    if request.method == 'POST':
        # Handle form submission
        price_str = request.form['price'].replace('.', '').replace(',', '').replace(' ', '')
        
        client_request = ClientRequest(
            full_name=request.form['full_name'],
            dni=request.form['dni'],
            phone_number=request.form['phone_number'],
            location=request.form['location'],
            address=request.form.get('address', ''),
            title=request.form['title'],
            description=request.form['description'],
            price=int(price_str),
            currency=request.form['currency'],
            publication_type=request.form.get('publication_type', 'plus'),
            year=int(request.form['year']) if request.form['year'] else None,
            brand=request.form['brand'],
            model=request.form['model'],
            kilometers=int(request.form['kilometers'].replace('.', '').replace(',', '').replace(' ', '')) if request.form['kilometers'] else None,
            fuel_type=request.form['fuel_type'],
            transmission=request.form['transmission'],
            color=request.form['color']
        )
        
        # Handle uploaded images
        image_urls = []
        if 'vehicle_images' in request.files:
            files = request.files.getlist('vehicle_images')
            for file in files:
                if file and file.filename and allowed_file(file.filename):
                    # Generate unique filename
                    filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                    filename = f"client_{timestamp}_{filename}"
                    
                    # Save file
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    
                    # Store relative URL
                    image_urls.append(f"uploads/{filename}")
        
        client_request.images = json.dumps(image_urls)
        
        db.session.add(client_request)
        db.session.commit()
        
        flash('Tu solicitud ha sido enviada exitosamente. La revisaremos y te contactaremos pronto.', 'success')
        return redirect(url_for('index'))
    
    return render_template('client_request.html')

@app.route('/admin/solicitudes-pendientes')
def admin_pending_requests():
    if not session.get('admin_logged_in'):
        return redirect(url_for('panel_login'))
    
    pending_requests = ClientRequest.query.filter_by(status='pending').order_by(ClientRequest.created_at.desc()).all()
    
    return render_template('admin_pending_requests.html', requests=pending_requests)

@app.route('/admin/procesar-solicitud/<int:request_id>/<action>')
def process_client_request(request_id, action):
    if not session.get('admin_logged_in'):
        return redirect(url_for('panel_login'))
    
    client_request = ClientRequest.query.get_or_404(request_id)
    admin_id = session.get('admin_id')
    
    if action == 'approve':
        try:
            # Get premium duration from query parameter
            duration_months = int(request.args.get('duration', 1))
            print(f"Processing approval for request {request_id} with duration {duration_months} months")
            
            # Create vehicle from client request
            vehicle = Vehicle(
                title=client_request.title,
                description=client_request.description,
                price=client_request.price,
                currency=client_request.currency,
                year=client_request.year,
                brand=client_request.brand,
                model=client_request.model,
                kilometers=client_request.kilometers,
                fuel_type=client_request.fuel_type,
                transmission=client_request.transmission,
                color=client_request.color,
                images=client_request.images,
                whatsapp_number=client_request.phone_number,
                is_plus=(client_request.publication_type == 'plus'),
                client_request_id=client_request.id,
                premium_duration_months=duration_months
            )
            
            # Set premium expiration date
            from datetime import datetime, timedelta
            vehicle.premium_expires_at = datetime.utcnow() + timedelta(days=duration_months * 30)
            
            db.session.add(vehicle)
            client_request.status = 'approved'
            client_request.processed_at = datetime.utcnow()
            client_request.processed_by_admin_id = admin_id
            
            db.session.commit()
            print(f"Successfully approved request {request_id}")
            flash(f'Solicitud aprobada y vehículo publicado: {vehicle.title} (Premium por {duration_months} meses)', 'success')
            
        except Exception as e:
            db.session.rollback()
            print(f"Error approving request {request_id}: {str(e)}")
            flash(f'Error al aprobar la solicitud: {str(e)}', 'error')
    
    elif action == 'reject':
        client_request.status = 'rejected'
        client_request.processed_at = datetime.utcnow()
        client_request.processed_by_admin_id = admin_id
        
        flash(f'Solicitud rechazada: {client_request.title}', 'warning')
    
    db.session.commit()
    return redirect(url_for('admin_pending_requests'))

@app.route('/admin/editar-solicitud/<int:request_id>', methods=['GET', 'POST'])
def edit_client_request(request_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('panel_login'))
    
    client_request = ClientRequest.query.get_or_404(request_id)
    
    if request.method == 'POST':
        # Update client request data
        price_str = request.form['price'].replace('.', '').replace(',', '').replace(' ', '')
        
        client_request.full_name = request.form['full_name']
        client_request.dni = request.form['dni']
        client_request.phone_number = request.form['phone_number']
        client_request.location = request.form['location']
        client_request.address = request.form.get('address', '')
        client_request.title = request.form['title']
        client_request.description = request.form['description']
        client_request.price = int(price_str)
        client_request.currency = request.form['currency']
        client_request.year = int(request.form['year']) if request.form['year'] else None
        client_request.brand = request.form['brand']
        client_request.model = request.form['model']
        client_request.kilometers = int(request.form['kilometers'].replace('.', '').replace(',', '').replace(' ', '')) if request.form['kilometers'] else None
        client_request.fuel_type = request.form['fuel_type']
        client_request.transmission = request.form['transmission']
        client_request.color = request.form['color']
        client_request.admin_notes = request.form.get('admin_notes', '')
        
        # Handle new uploaded images
        if 'vehicle_images' in request.files:
            files = request.files.getlist('vehicle_images')
            if any(file.filename for file in files):  # If new images are uploaded
                new_image_urls = []
                for file in files:
                    if file and file.filename and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                        filename = f"client_{timestamp}_{filename}"
                        
                        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        file.save(file_path)
                        
                        new_image_urls.append(f"uploads/{filename}")
                
                if new_image_urls:  # Replace images only if new ones were uploaded
                    client_request.images = json.dumps(new_image_urls)
        
        db.session.commit()
        flash('Solicitud actualizada exitosamente', 'success')
        return redirect(url_for('admin_pending_requests'))
    
    return render_template('edit_client_request.html', client_request=client_request)

@app.route('/admin/usuarios-vehiculos')
def admin_users_vehicles():
    if not session.get('admin_logged_in'):
        return redirect(url_for('panel_login'))
    
    # Get all vehicles grouped by owner (from client request)
    from sqlalchemy import distinct
    
    # Get vehicles with their original client request data
    vehicles_with_owners = db.session.query(
        Vehicle, ClientRequest
    ).join(
        ClientRequest, Vehicle.client_request_id == ClientRequest.id
    ).order_by(ClientRequest.full_name, Vehicle.created_at.desc()).all()
    
    # Group vehicles by owner
    owners = {}
    for vehicle, client_request in vehicles_with_owners:
        owner_key = f"{client_request.full_name} ({client_request.dni})"
        if owner_key not in owners:
            owners[owner_key] = {
                'client_data': client_request,
                'vehicles': []
            }
        owners[owner_key]['vehicles'].append(vehicle)
    
    from datetime import datetime
    now = datetime.utcnow()
    return render_template('admin_users_vehicles.html', owners=owners, now=now)

@app.route('/admin/update-premium-duration/<int:vehicle_id>/<int:months>', methods=['POST'])
def update_premium_duration(vehicle_id, months):
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'No autorizado'})
    
    if months < 1 or months > 12:
        return jsonify({'success': False, 'error': 'Duración inválida'})
    
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    
    # Update premium duration
    vehicle.premium_duration_months = months
    
    # Calculate new expiration date
    from datetime import datetime, timedelta
    if vehicle.premium_expires_at and vehicle.premium_expires_at > datetime.utcnow():
        # Extend from current expiration date
        vehicle.premium_expires_at = vehicle.premium_expires_at + timedelta(days=months * 30)
    else:
        # Set new expiration date from now
        vehicle.premium_expires_at = datetime.utcnow() + timedelta(days=months * 30)
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': f'Duración premium actualizada a {months} meses'})

@app.route('/admin/toggle-vehicle/<int:vehicle_id>')
def toggle_vehicle_status(vehicle_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('panel_login'))
    
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    vehicle.is_active = not vehicle.is_active
    db.session.commit()
    
    status_text = "activado" if vehicle.is_active else "pausado"
    flash(f'Vehículo "{vehicle.title}" ha sido {status_text}', 'success')
    return redirect(url_for('admin_users_vehicles'))

@app.route('/admin/delete-vehicle/<int:vehicle_id>', methods=['DELETE'])
def delete_vehicle_ajax(vehicle_id):
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'No autorizado'})
    
    try:
        vehicle = Vehicle.query.get_or_404(vehicle_id)
        
        # Delete associated images from filesystem
        import os
        upload_folder = app.config['UPLOAD_FOLDER']
        
        if vehicle.images:
            for image_path in vehicle.images:
                full_path = os.path.join(upload_folder, image_path)
                if os.path.exists(full_path):
                    try:
                        os.remove(full_path)
                    except OSError as e:
                        print(f"Error deleting image {full_path}: {e}")
        
        # Delete vehicle from database
        db.session.delete(vehicle)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Vehículo "{vehicle.brand} {vehicle.model}" eliminado correctamente'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False, 
            'error': f'Error al eliminar el vehículo: {str(e)}'
        })


# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('base.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('base.html'), 500
