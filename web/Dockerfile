FROM nginx:alpine

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/

# Copy static files to nginx html directory
COPY . /usr/share/nginx/html

# Expose port 8080 (Cloud Run default)
EXPOSE 8080

# Run nginx
CMD ["nginx", "-g", "daemon off;"]
